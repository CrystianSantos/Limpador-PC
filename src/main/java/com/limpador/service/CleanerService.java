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
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
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
                if (!Files.exists(p) || !Files.isRegularFile(p)) {
                    continue;
                }

                // Validação de Escopo: O arquivo DEVE residir em uma das pastas temporárias aprovadas
                boolean withinSafeScope = approvedTempRoots.stream()
                        .anyMatch(root -> p.startsWith(root.toAbsolutePath().normalize()));

                if (!withinSafeScope) {
                    log.warn("Arquivo fora do escopo de pastas temporárias seguras rejeitado: {}", p);
                    skipped++;
                    continue;
                }

                // Validação Dupla de Idade (re-checagem no momento da exclusão)
                try {
                    BasicFileAttributes attrs = Files.readAttributes(p, BasicFileAttributes.class);
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
            messages.add("Excluindo cópias duplicadas autorizadas...");

            // Constrói conjunto de cópias genuinamente identificadas na varredura
            Set<String> verifiedCopyPaths = new HashSet<>();
            if (duplicateGroups != null) {
                for (DuplicateGroup group : duplicateGroups) {
                    if (group.getCopies() != null) {
                        for (FileItem copy : group.getCopies()) {
                            verifiedCopyPaths.add(Paths.get(copy.getPath()).toAbsolutePath().normalize().toString());
                        }
                    }
                }
            }

            for (String copyPath : request.getSelectedCopies()) {
                Path p = Paths.get(copyPath).toAbsolutePath().normalize();

                // Segurança: Recusa qualquer caminho que NÃO foi identificado na varredura
                if (!verifiedCopyPaths.contains(p.toString())) {
                    log.warn("Tentativa de exclusão bloqueada: caminho não pertence às cópias identificadas: {}", p);
                    skipped++;
                    continue;
                }

                if (!Files.isRegularFile(p)) {
                    continue;
                }

                try {
                    long size = Files.size(p);
                    if (safeDelete(p)) {
                        deleted++;
                        freedBytes += size;
                    } else {
                        skipped++;
                    }
                } catch (Exception e) {
                    skipped++;
                }
            }
            messages.add("Cópias duplicadas selecionadas e validadas foram removidas.");
        }

        return new CleanResult(true, deleted, skipped, freedBytes, messages);
    }

    /**
     * Tenta excluir o arquivo apenas se não estiver em uso e sem forçar permissões.
     * Não altera atributos do sistema operacional (não força setWritable).
     */
    private boolean safeDelete(Path path) {
        try {
            // Verifica se o arquivo pode ser aberto para escrita (confirmação ativa de lock)
            try (FileChannel channel = FileChannel.open(path, StandardOpenOption.WRITE)) {
                // Arquivo livre para manipulação
            } catch (Exception locked) {
                log.debug("Arquivo em uso ou com acesso restrito: {}", path);
                return false;
            }

            Files.deleteIfExists(path);
            return true;
        } catch (IOException | SecurityException e) {
            log.debug("Falha na exclusão de {}: {}", path, e.getMessage());
            return false;
        }
    }
}
