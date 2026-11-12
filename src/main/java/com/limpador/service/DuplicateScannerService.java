package com.limpador.service;

import com.limpador.model.DuplicateGroup;
import com.limpador.model.FileItem;
import com.limpador.util.PlatformUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Serviço de detecção de arquivos duplicados com algoritmo em 3 fases:
 * 1. Agrupamento preliminar por tamanho exato em bytes.
 * 2. Hash parcial rápido (primeiros 8 KB) para descartar arquivos diferentes.
 * 3. Confirmação com SHA-256 criptográfico para integridade total.
 */
@Service
public class DuplicateScannerService {

    private static final Logger log = LoggerFactory.getLogger(DuplicateScannerService.class);

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss")
            .withZone(ZoneId.systemDefault());

    private static final long MIN_FILE_SIZE = 1024L; // 1 KB mínimo para ignorar arquivos vazios
    private static final int PARTIAL_CHUNK_SIZE = 8192; // 8 KB para verificação preliminar

    public List<DuplicateGroup> scan(Collection<Path> customDirectories) {
        Collection<Path> targetDirs = (customDirectories != null && !customDirectories.isEmpty())
                ? customDirectories
                : PlatformUtils.getUserScanDirectories().values();

        Set<String> excluded = PlatformUtils.getSystemExcludedFolders();
        Map<Long, List<PathRecord>> sizeMap = new HashMap<>();

        // FASE 1: Agrupamento inicial por tamanho exato utilizando walkFileTree resiliente
        for (Path dir : targetDirs) {
            if (!Files.isDirectory(dir)) {
                continue;
            }

            try {
                Files.walkFileTree(dir, EnumSet.of(FileVisitOption.FOLLOW_LINKS), 12, new SimpleFileVisitor<>() {
                    @Override
                    public FileVisitResult preVisitDirectory(Path d, BasicFileAttributes attrs) {
                        String name = d.getFileName() != null ? d.getFileName().toString().toLowerCase() : "";
                        if (excluded.contains(name)) {
                            return FileVisitResult.SKIP_SUBTREE;
                        }
                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        if (attrs.isRegularFile() && attrs.size() >= MIN_FILE_SIZE) {
                            try {
                                sizeMap.computeIfAbsent(attrs.size(), k -> new ArrayList<>())
                                        .add(new PathRecord(file, attrs.size(), attrs.lastModifiedTime().toInstant()));
                            } catch (Exception e) {
                                log.debug("Não foi possível registrar arquivo: {}", file, e);
                            }
                        }
                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFileFailed(Path file, IOException exc) {
                        // Resiliente: continua mesmo se não tiver permissão em um arquivo/pasta
                        log.debug("Acesso negado ou erro ao visitar: {}", file);
                        return FileVisitResult.CONTINUE;
                    }
                });
            } catch (Exception e) {
                log.warn("Erro ao varrer diretório {}: {}", dir, e.getMessage());
            }
        }

        // Filtra tamanhos que possuem 2 ou mais arquivos
        Map<String, List<PathRecord>> partialHashMap = new HashMap<>();

        // FASE 2: Hash parcial de 8 KB para descartar rapidamente não-duplicados
        for (Map.Entry<Long, List<PathRecord>> entry : sizeMap.entrySet()) {
            if (entry.getValue().size() < 2) continue;

            for (PathRecord rec : entry.getValue()) {
                String partialHash = computePartialHash(rec.path);
                if (partialHash != null) {
                    String key = rec.size + "_" + partialHash;
                    partialHashMap.computeIfAbsent(key, k -> new ArrayList<>()).add(rec);
                }
            }
        }

        // FASE 3: Confirmação completa com hash criptográfico SHA-256
        List<DuplicateGroup> resultGroups = new ArrayList<>();

        for (List<PathRecord> candidates : partialHashMap.values()) {
            if (candidates.size() < 2) continue;

            Map<String, List<PathRecord>> fullHashMap = new HashMap<>();
            for (PathRecord rec : candidates) {
                String fullHash = computeFullSha256(rec.path);
                if (fullHash != null) {
                    fullHashMap.computeIfAbsent(fullHash, k -> new ArrayList<>()).add(rec);
                }
            }

            for (Map.Entry<String, List<PathRecord>> fullEntry : fullHashMap.entrySet()) {
                List<PathRecord> dupList = fullEntry.getValue();
                if (dupList.size() > 1) {
                    // Ordena pelo arquivo mais antigo para ser o ORIGINAL seguro
                    dupList.sort(Comparator.comparing(r -> r.mtime));

                    PathRecord origRecord = dupList.get(0);
                    FileItem origItem = new FileItem(
                            origRecord.path.toAbsolutePath().toString(),
                            origRecord.path.getFileName().toString(),
                            "Original",
                            origRecord.size,
                            FORMATTER.format(origRecord.mtime),
                            false,
                            false // Não apagar por padrão
                    );

                    List<FileItem> copyItems = new ArrayList<>();
                    for (int i = 1; i < dupList.size(); i++) {
                        PathRecord copyRec = dupList.get(i);
                        copyItems.add(new FileItem(
                                copyRec.path.toAbsolutePath().toString(),
                                copyRec.path.getFileName().toString(),
                                "Cópia",
                                copyRec.size,
                                FORMATTER.format(copyRec.mtime),
                                false,
                                true // Sugerido para exclusão
                        ));
                    }

                    resultGroups.add(new DuplicateGroup(
                            fullEntry.getKey(),
                            origRecord.size,
                            origItem,
                            copyItems
                    ));
                }
            }
        }

        return resultGroups;
    }

    private String computePartialHash(Path path) {
        try (InputStream in = Files.newInputStream(path)) {
            byte[] buffer = new byte[PARTIAL_CHUNK_SIZE];
            int read = in.read(buffer);
            if (read <= 0) return null;

            MessageDigest md = MessageDigest.getInstance("MD5");
            md.update(buffer, 0, read);
            return bytesToHex(md.digest());
        } catch (Exception e) {
            return null;
        }
    }

    private String computeFullSha256(Path path) {
        try (InputStream in = Files.newInputStream(path)) {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[65536];
            int read;
            while ((read = in.read(buffer)) != -1) {
                md.update(buffer, 0, read);
            }
            return bytesToHex(md.digest());
        } catch (Exception e) {
            return null;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private record PathRecord(Path path, long size, Instant mtime) {
    }
}
