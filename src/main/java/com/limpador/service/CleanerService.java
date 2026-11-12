package com.limpador.service;

import com.limpador.model.CleanRequest;
import com.limpador.model.CleanResult;
import com.limpador.model.FileItem;
import com.limpador.model.ScanSummary;
import com.limpador.util.PlatformUtils;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

@Service
public class CleanerService {

    public CleanResult clean(CleanRequest request, ScanSummary tempSummary, ScanSummary trashSummary) {
        int deleted = 0;
        int skipped = 0;
        long freedBytes = 0;
        List<String> messages = new ArrayList<>();

        // 1. Limpeza de Temporários
        if (request.isAuthTemp() && tempSummary != null && tempSummary.getItems() != null) {
            messages.add("Iniciando limpeza de arquivos temporários...");
            for (FileItem item : tempSummary.getItems()) {
                if (item.isDir()) continue;

                Path p = Paths.get(item.getPath());
                if (!Files.exists(p)) continue;

                if (safeDelete(p)) {
                    deleted++;
                    freedBytes += item.getSize();
                } else {
                    skipped++;
                }
            }
            messages.add("Temporários limpos. Arquivos em uso foram preservados com segurança.");
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

        // 3. Exclusão de Cópias Duplicadas Selecionadas
        if (request.isAuthDuplicates() && request.getSelectedCopies() != null) {
            messages.add("Excluindo cópias duplicadas autorizadas...");
            for (String copyPath : request.getSelectedCopies()) {
                Path p = Paths.get(copyPath);
                if (!Files.isRegularFile(p)) continue;

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
            messages.add("Cópias duplicadas selecionadas foram removidas.");
        }

        return new CleanResult(true, deleted, skipped, freedBytes, messages);
    }

    private boolean safeDelete(Path path) {
        try {
            File f = path.toFile();
            if (!f.canWrite()) {
                f.setWritable(true);
            }
            Files.deleteIfExists(path);
            return true;
        } catch (IOException | SecurityException e) {
            return false; // Arquivo em uso ou protegido
        }
    }
}
