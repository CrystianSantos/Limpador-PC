package com.limpador.service;

import com.limpador.model.FileItem;
import com.limpador.model.ScanSummary;
import com.limpador.util.PlatformUtils;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.*;
import java.util.*;

@Service
public class TrashScannerService {

    public ScanSummary scan() {
        List<FileItem> items = new ArrayList<>();
        long totalSize = 0;

        if (PlatformUtils.isWindows()) {
            items = scanWindowsRecycleBin();
        } else if (PlatformUtils.isMac()) {
            items = scanMacTrash();
        } else {
            items = scanLinuxTrash();
        }

        for (FileItem it : items) {
            totalSize += it.getSize();
        }

        String explanation = "A Lixeira armazena arquivos e pastas que você excluiu no passado. "
                + "Eles continuam ocupando espaço físico no disco rígido até que a Lixeira seja esvaziada. "
                + "Você pode verificar os itens listados antes de autorizar o esvaziamento.";

        return new ScanSummary(
                "Lixeira do Sistema (" + PlatformUtils.getOsDisplayName() + ")",
                items.size(),
                totalSize,
                explanation,
                true,
                items
        );
    }

    private List<FileItem> scanWindowsRecycleBin() {
        List<FileItem> list = new ArrayList<>();
        String psCode = "$shell = New-Object -ComObject Shell.Application; "
                + "$bin = $shell.Namespace(0xa); "
                + "if ($bin -ne $null) { foreach ($i in $bin.Items()) { Write-Output ($i.Name + '||' + $i.Size + '||' + $i.Type + '||' + $i.Path) } }";

        try {
            ProcessBuilder pb = new ProcessBuilder("powershell", "-NoProfile", "-Command", psCode);
            Process proc = pb.start();

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(proc.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty()) continue;

                    String[] parts = line.split("\\|\\|");
                    String name = parts.length > 0 ? parts[0] : "Item";
                    long size = 0;
                    if (parts.length > 1) {
                        try { size = Long.parseLong(parts[1]); } catch (Exception ignored) {}
                    }
                    String type = parts.length > 2 ? parts[2] : "Arquivo";
                    String path = parts.length > 3 ? parts[3] : "";

                    list.add(new FileItem(path, name, type, size, "-", false, true));
                }
            }
            proc.waitFor();
        } catch (Exception ignored) {
        }
        return list;
    }

    private List<FileItem> scanMacTrash() {
        List<FileItem> list = new ArrayList<>();
        String home = System.getProperty("user.home");
        if (home == null) return list;

        Path trash = Paths.get(home, ".Trash");
        if (!Files.isDirectory(trash)) return list;

        try (var stream = Files.newDirectoryStream(trash)) {
            for (Path entry : stream) {
                try {
                    long size = Files.isRegularFile(entry) ? Files.size(entry) : calculateDirSize(entry);
                    list.add(new FileItem(
                            entry.toAbsolutePath().toString(),
                            entry.getFileName().toString(),
                            Files.isDirectory(entry) ? "Pasta" : "Arquivo",
                            size,
                            "-",
                            Files.isDirectory(entry),
                            true
                    ));
                } catch (Exception ignored) {}
            }
        } catch (Exception ignored) {}
        return list;
    }

    private List<FileItem> scanLinuxTrash() {
        List<FileItem> list = new ArrayList<>();
        String home = System.getProperty("user.home");
        if (home == null) return list;

        Path trash = Paths.get(home, ".local", "share", "Trash", "files");
        if (!Files.isDirectory(trash)) return list;

        try (var stream = Files.newDirectoryStream(trash)) {
            for (Path entry : stream) {
                try {
                    long size = Files.isRegularFile(entry) ? Files.size(entry) : calculateDirSize(entry);
                    list.add(new FileItem(
                            entry.toAbsolutePath().toString(),
                            entry.getFileName().toString(),
                            Files.isDirectory(entry) ? "Pasta" : "Arquivo",
                            size,
                            "-",
                            Files.isDirectory(entry),
                            true
                    ));
                } catch (Exception ignored) {}
            }
        } catch (Exception ignored) {}
        return list;
    }

    private long calculateDirSize(Path dir) {
        long total = 0;
        try (var stream = Files.walk(dir, 3)) {
            for (Path p : (Iterable<Path>) stream::iterator) {
                if (Files.isRegularFile(p)) {
                    total += Files.size(p);
                }
            }
        } catch (Exception ignored) {}
        return total;
    }
}
