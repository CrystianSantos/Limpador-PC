package com.limpador.service;

import com.limpador.model.CleanRequest;
import com.limpador.model.CleanResult;
import com.limpador.model.DuplicateGroup;
import com.limpador.model.FileItem;
import com.limpador.model.ScanSummary;
import com.limpador.util.PlatformUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * Serviço responsável pela execução segura e controlada de limpeza.
 * Implementa validação estrita de escopo para impedir exclusões não autorizadas,
 * checagem dupla de buffer temporal e detecção de arquivos em uso.
 */
@Service
public class CleanerService {

    private static final Logger log = LoggerFactory.getLogger(CleanerService.class);
    private static final int SAFE_BUFFER_MINUTES = 5;

    /** Backwards-compatible entry point for callers that do not have duplicate scan results. */
    public CleanResult clean(CleanRequest request, ScanSummary tempSummary, ScanSummary trashSummary) {
        return clean(request, tempSummary, trashSummary, null);
    }

    public CleanResult clean(
            CleanRequest request,
            ScanSummary tempSummary,
            ScanSummary trashSummary,
            List<DuplicateGroup> duplicateGroups
    ) {
        int deleted = 0;
        int skipped = 0;
        long freedBytes = 0;
        List<String> messages = new ArrayList<>();

        // 1. Limpeza de Arquivos Temporários
        if (request.isAuthTemp() && tempSummary != null && tempSummary.getItems() != null) {
            messages.add("Iniciando limpeza de arquivos temporários autorizados...");
            Collection<Path> approvedTempRoots = PlatformUtils.getSafeTempDirectories().values();
            Instant safeTimeThreshold = Instant.now().minus(SAFE_BUFFER_MINUTES, ChronoUnit.MINUTES);

            for (FileItem item : tempSummary.getItems()) {
                if (item.isDir()) {
                    continue;
                }

                Path p = Paths.get(item.getPath()).toAbsolutePath().normalize();
                if (!Files.isRegularFile(p, LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(p)) {
                    continue;
                }

                // Validação de Escopo: O arquivo DEVE residir em uma das pastas temporárias aprovadas
                boolean withinSafeScope = approvedTempRoots.stream().anyMatch(root -> {
                    try {
                        return p.toRealPath().startsWith(root.toRealPath());
                    } catch (IOException e) {
                        return false;
                    }
                });

                if (!withinSafeScope) {
                    log.warn("Arquivo fora do escopo de pastas temporárias seguras rejeitado: {}", p);
                    skipped++;
                    continue;
                }

                // Validação Dupla de Idade (re-checagem no momento da exclusão)
                try {
                    BasicFileAttributes attrs = Files.readAttributes(p, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                    if (attrs.lastModifiedTime().toInstant().isAfter(safeTimeThreshold)) {
                        log.debug("Arquivo modificado recentemente preservado: {}", p);
                        skipped++;
                        continue;
                    }

                    long fileSize = attrs.size();
                    if (safeDelete(p)) {
                        deleted++;
                        freedBytes += fileSize;
                    } else {
                        skipped++;
                    }
                } catch (Exception e) {
                    skipped++;
                }
            }
            messages.add("Temporários processados. Arquivos em uso ou recentes foram preservados.");
        }

        // 2. Esvaziamento da Lixeira
        if (request.isAuthRecycle() && trashSummary != null) {
            messages.add("Esvaziando lixeira do sistema...");
            boolean ok = PlatformUtils.emptyTrash();
            if (ok) {
                freedBytes += trashSummary.getTotalSize();
                deleted += trashSummary.getTotalFiles();
                messages.add("Lixeira esvaziada com sucesso.");
            } else {
                messages.add("Aviso: Não foi possível esvaziar totalmente a lixeira.");
            }
        }

        // 3. Exclusão de Cópias Duplicadas Selecionadas (Validação Estrita de Escopo)
        if (request.isAuthDuplicates() && request.getSelectedCopies() != null && !request.getSelectedCopies().isEmpty()) {
            boolean deletePermanently = request.isDeleteDuplicatesPermanently();
            messages.add(deletePermanently
                    ? "Apagando permanentemente as cópias duplicadas autorizadas..."
                    : "Movendo as cópias duplicadas autorizadas para a Lixeira...");

            // Constrói conjunto de cópias genuinamente identificadas na varredura
            Map<String, String> verifiedCopyHashes = new HashMap<>();
            if (duplicateGroups != null) {
                for (DuplicateGroup group : duplicateGroups) {
                    if (group.getCopies() != null) {
                        for (FileItem copy : group.getCopies()) {
                            verifiedCopyHashes.put(Paths.get(copy.getPath()).toAbsolutePath().normalize().toString(), group.getHash());
                        }
                    }
                }
            }

            for (String copyPath : request.getSelectedCopies()) {
                Path p = Paths.get(copyPath).toAbsolutePath().normalize();

                // Segurança: Recusa qualquer caminho que NÃO foi identificado na varredura
                String expectedHash = verifiedCopyHashes.get(p.toString());
                if (expectedHash == null) {
                    log.warn("Tentativa de exclusão bloqueada: caminho não pertence às cópias identificadas: {}", p);
                    skipped++;
                    continue;
                }

                if (!Files.isRegularFile(p, LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(p)) {
                    skipped++;
                    continue;
                }

                try {
                    BasicFileAttributes attrs = Files.readAttributes(p, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                    if (attrs.size() < 1024 || !expectedHash.equalsIgnoreCase(sha256(p))) {
                        skipped++;
                        continue;
                    }
                    long size = attrs.size();
                    boolean removed = deletePermanently ? safeDelete(p) : PlatformUtils.moveToTrash(p);
                    if (removed) {
                        deleted++;
                        if (deletePermanently) freedBytes += size;
                    } else {
                        skipped++;
                    }
                } catch (Exception e) {
                    skipped++;
                }
            }
            messages.add(deletePermanently
                    ? "Cópias selecionadas foram apagadas permanentemente."
                    : "As cópias compatíveis foram movidas para a Lixeira; isso não libera espaço até esvaziá-la. Cópias não suportadas foram preservadas.");
            if (skipped > 0) messages.add("Alguns itens foram preservados ou ignorados. Verifique a contagem de itens ignorados.");
        }

        return new CleanResult(true, deleted, skipped, freedBytes, messages);
    }

    private String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (var input = Files.newInputStream(path)) {
            byte[] buffer = new byte[65536];
            int read;
            while ((read = input.read(buffer)) != -1) digest.update(buffer, 0, read);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    /** Attempt deletion directly; a write-open is neither a reliable lock check nor harmless. */
    private boolean safeDelete(Path path) {
        try {
            Files.deleteIfExists(path);
            return true;
        } catch (IOException | SecurityException e) {
            log.debug("Falha na exclusão de {}: {}", path, e.getMessage());
            return false;
        }
    }
}
