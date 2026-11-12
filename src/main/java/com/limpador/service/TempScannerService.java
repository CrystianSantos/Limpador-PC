package com.limpador.service;

import com.limpador.model.FileItem;
import com.limpador.model.ScanSummary;
import com.limpador.util.PlatformUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * Serviço de varredura de arquivos temporários e mortos do sistema operacional.
 * Inclui proteções essenciais para estabilidade:
 * 1. Buffer de segurança de 5 minutos (não toca em arquivos recém-criados/modificados).
 * 2. Detecção de bloqueio em nível de FileChannel (ignora arquivos em uso por outros processos).
 * 3. Varredura resiliente que não aborta caso encontre diretórios de sistema protegidos.
 */
@Service
public class TempScannerService {

    private static final Logger log = LoggerFactory.getLogger(TempScannerService.class);

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss")
            .withZone(ZoneId.systemDefault());

    public ScanSummary scan() {
        List<FileItem> items = new ArrayList<>();
        long totalSize = 0;
        int fileCount = 0;

        Map<String, Path> safeDirs = PlatformUtils.getSafeTempDirectories();
        Instant safeTimeThreshold = Instant.now().minus(5, ChronoUnit.MINUTES);

        for (Map.Entry<String, Path> entry : safeDirs.entrySet()) {
            String category = entry.getKey();
            Path dirPath = entry.getValue();

            if (!Files.isDirectory(dirPath)) {
                continue;
            }

            try {
                Files.walkFileTree(dirPath, EnumSet.noneOf(FileVisitOption.class), 6, new SimpleFileVisitor<>() {
                    @Override
                    public FileVisitResult visitFile(Path p, BasicFileAttributes attrs) {
                        if (attrs.isRegularFile()) {
                            try {
                                Instant lastMod = attrs.lastModifiedTime().toInstant();

                                // Regra de segurança: Não mexer em arquivos modificados nos últimos 5 minutos
                                if (lastMod.isAfter(safeTimeThreshold)) {
                                    return FileVisitResult.CONTINUE;
                                }

                                // Verifica se o arquivo está bloqueado/em uso por outro processo
                                if (isFileLocked(p)) {
                                    return FileVisitResult.CONTINUE;
                                }

                                long size = attrs.size();
                                items.add(new FileItem(
                                        p.toAbsolutePath().toString(),
                                        p.getFileName() != null ? p.getFileName().toString() : "temp_file",
                                        category,
                                        size,
                                        FORMATTER.format(lastMod),
                                        false,
                                        true
                                ));

                            } catch (Exception e) {
                                log.debug("Erro ao ler atributos de arquivo temporário: {}", p);
                            }
                        }
                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFileFailed(Path file, IOException exc) {
                        log.debug("Acesso negado em arquivo/pasta temporária: {}", file);
                        return FileVisitResult.CONTINUE;
                    }
                });
            } catch (Exception e) {
                log.warn("Falha ao varrer pasta temporária {}: {}", dirPath, e.getMessage());
            }
        }

        for (FileItem item : items) {
            totalSize += item.getSize();
            fileCount++;
        }

        String explanation = "Arquivos temporários e mortos são resíduos gerados pelo Windows, navegadores e instaladores. "
                + "Além de %TEMP%, foram analisados relatórios de travamento (CrashDumps) e caches seguros. "
                + "Arquivos recentemente modificados ou atualmente em uso por programas abertos são automaticamente preservados.";

        return new ScanSummary(
                "Arquivos Temporários e Mortos (" + PlatformUtils.getOsDisplayName() + ")",
                fileCount,
                totalSize,
                explanation,
                true,
                items
        );
    }

    /**
     * Verifica de forma não bloqueante se o arquivo está aberto com bloqueio exclusivo por outro processo.
     */
    private boolean isFileLocked(Path path) {
        try (FileChannel channel = FileChannel.open(path, StandardOpenOption.READ)) {
            return false;
        } catch (Exception e) {
            return true; // Arquivo bloqueado ou inacessível no momento
        }
    }
}
