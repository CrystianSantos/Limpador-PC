package com.limpador.util;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

public final class PlatformUtils {

    private PlatformUtils() {
    }

    public static boolean isWindows() {
        return System.getProperty("os.name", "").toLowerCase().contains("win");
    }

    public static boolean isMac() {
        return System.getProperty("os.name", "").toLowerCase().contains("mac");
    }

    public static boolean isLinux() {
        String os = System.getProperty("os.name", "").toLowerCase();
        return os.contains("linux") || os.contains("unix");
    }

    public static String getOsDisplayName() {
        if (isWindows()) {
            return "Microsoft Windows";
        } else if (isMac()) {
            return "Apple macOS";
        } else {
            return "GNU/Linux";
        }
    }

    /**
     * Retorna diretórios temporários seguros para varredura.
     * Inclui %TEMP% e pastas auxiliares de cache e relatórios de falha
     * que não interferem no sistema operacional nem em programas ativos.
     */
    public static Map<String, Path> getSafeTempDirectories() {
        Map<String, Path> dirs = new LinkedHashMap<>();

        if (isWindows()) {
            String tempEnv = System.getenv("TEMP");
            if (tempEnv == null || tempEnv.isBlank()) {
                tempEnv = System.getenv("TMP");
            }
            if (tempEnv != null) {
                Path p = Paths.get(tempEnv);
                if (Files.isDirectory(p)) {
                    dirs.put("Temp do Usuário (%TEMP%)", p);
                }
            }

            String localAppData = System.getenv("LOCALAPPDATA");
            if (localAppData != null) {
                Path crashDumps = Paths.get(localAppData, "CrashDumps");
                if (Files.isDirectory(crashDumps)) {
                    dirs.put("Relatórios de Falhas de Programas (CrashDumps)", crashDumps);
                }

                Path inetCache = Paths.get(localAppData, "Microsoft", "Windows", "INetCache");
                if (Files.isDirectory(inetCache)) {
                    dirs.put("Cache de Rede do Windows (INetCache)", inetCache);
                }

                Path deliveryOpt = Paths.get(localAppData, "Microsoft", "Windows", "DeliveryOptimization", "Cache");
                if (Files.isDirectory(deliveryOpt)) {
                    dirs.put("Cache de Otimização de Entrega", deliveryOpt);
                }

                Path downloadedInst = Paths.get(localAppData, "Downloaded Installations");
                if (Files.isDirectory(downloadedInst)) {
                    dirs.put("Resíduos de Instaladores Antigos", downloadedInst);
                }
            }

            String systemRoot = System.getenv("SystemRoot");
            if (systemRoot == null) systemRoot = "C:\\Windows";
            Path winTemp = Paths.get(systemRoot, "Temp");
            if (Files.isDirectory(winTemp)) {
                dirs.put("Arquivos Temporários do Sistema Windows", winTemp);
            }

        } else if (isMac()) {
            String tmpDir = System.getenv("TMPDIR");
            if (tmpDir != null) {
                Path p = Paths.get(tmpDir);
                if (Files.isDirectory(p)) {
                    dirs.put("Cache Temporário do Usuário ($TMPDIR)", p);
                }
            }

            String userHome = System.getProperty("user.home");
            if (userHome != null) {
                Path caches = Paths.get(userHome, "Library", "Caches");
                if (Files.isDirectory(caches)) {
                    dirs.put("Caches de Aplicativos (~/Library/Caches)", caches);
                }
                Path logs = Paths.get(userHome, "Library", "Logs");
                if (Files.isDirectory(logs)) {
                    dirs.put("Logs de Diagnóstico Antigos (~/Library/Logs)", logs);
                }
            }

            for (String sysPath : List.of("/tmp", "/var/tmp")) {
                Path p = Paths.get(sysPath);
                if (Files.isDirectory(p)) {
                    dirs.put("Temporários do Sistema (" + sysPath + ")", p);
                }
            }

        } else { // Linux
            String userHome = System.getProperty("user.home");
            if (userHome != null) {
                Path cache = Paths.get(userHome, ".cache");
                if (Files.isDirectory(cache)) {
                    dirs.put("Cache do Usuário (~/.cache)", cache);
                }
            }

            for (String sysPath : List.of("/tmp", "/var/tmp")) {
                Path p = Paths.get(sysPath);
                if (Files.isDirectory(p)) {
                    dirs.put("Temporários do Sistema (" + sysPath + ")", p);
                }
            }
        }

        return dirs;
    }

    /**
     * Retorna diretórios pessoais comuns do usuário para varredura de duplicados.
     */
    public static Map<String, Path> getUserScanDirectories() {
        Map<String, Path> dirs = new LinkedHashMap<>();
        String userHome = System.getProperty("user.home");
        if (userHome == null) return dirs;

        Path home = Paths.get(userHome);
        List<Map.Entry<String, String>> candidates = List.of(
                Map.entry("Downloads", "Downloads"),
                Map.entry("Documentos", "Documents"),
                Map.entry("Área de Trabalho", "Desktop"),
                Map.entry("Imagens", "Pictures"),
                Map.entry("Vídeos", "Videos"),
                Map.entry("Música", "Music")
        );

        for (var entry : candidates) {
            Path p = home.resolve(entry.getValue());
            if (Files.isDirectory(p)) {
                dirs.put(entry.getKey(), p);
            }
        }

        return dirs;
    }

    /**
     * Pastas de sistema que devem ser ignoradas na busca de duplicados.
     */
    public static Set<String> getSystemExcludedFolders() {
        Set<String> set = new HashSet<>(List.of(
                ".git", "node_modules", "__pycache__", ".vscode", ".idea",
                "venv", "env", ".env", ".cache", ".npm", ".yarn", "target", "build"
        ));

        if (isWindows()) {
            set.addAll(List.of(
                    "appdata", "localappdata", "$recycle.bin", "system volume information",
                    "windows", "program files", "program files (x86)", "perflogs"
            ));
        } else if (isMac()) {
            set.addAll(List.of(
                    "library", "system", "applications", ".trash", ".ds_store",
                    ".spotlight-v100", ".fseventsd"
            ));
        } else {
            set.addAll(List.of(
                    "proc", "sys", "dev", "etc", "var", "usr", "boot", "run"
            ));
        }

        return set;
    }

    /**
     * Esvazia a Lixeira no Windows, macOS ou Linux.
     */
    public static boolean emptyTrash() {
        if (isWindows()) {
            try {
                ProcessBuilder pb = new ProcessBuilder(
                        "powershell", "-NoProfile", "-Command",
                        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
                );
                Process proc = pb.start();
                proc.waitFor();
                return proc.exitValue() == 0;
            } catch (Exception e) {
                return false;
            }
        } else if (isMac()) {
            try {
                ProcessBuilder pb = new ProcessBuilder(
                        "osascript", "-e", "tell application \"Finder\" to empty trash"
                );
                Process proc = pb.start();
                proc.waitFor();
                return proc.exitValue() == 0;
            } catch (Exception e) {
                // Fallback: remover ~/.Trash
                Path trash = Paths.get(System.getProperty("user.home"), ".Trash");
                deleteDirectoryContents(trash);
                return true;
            }
        } else {
            // Linux: ~/.local/share/Trash/files e info
            String home = System.getProperty("user.home");
            if (home != null) {
                Path trashFiles = Paths.get(home, ".local", "share", "Trash", "files");
                Path trashInfo = Paths.get(home, ".local", "share", "Trash", "info");
                deleteDirectoryContents(trashFiles);
                deleteDirectoryContents(trashInfo);
                return true;
            }
            return false;
        }
    }

    private static void deleteDirectoryContents(Path dir) {
        if (!Files.isDirectory(dir)) return;
        try (var stream = Files.newDirectoryStream(dir)) {
            for (Path entry : stream) {
                try {
                    if (Files.isDirectory(entry)) {
                        deleteDirectoryRecursively(entry);
                    } else {
                        Files.deleteIfExists(entry);
                    }
                } catch (IOException ignored) {
                }
            }
        } catch (IOException ignored) {
        }
    }

    private static void deleteDirectoryRecursively(Path dir) throws IOException {
        if (Files.isDirectory(dir)) {
            try (var stream = Files.newDirectoryStream(dir)) {
                for (Path entry : stream) {
                    deleteDirectoryRecursively(entry);
                }
            }
        }
        Files.deleteIfExists(dir);
    }
}
