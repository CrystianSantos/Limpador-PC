package com.limpador.controller;

import com.limpador.model.*;
import com.limpador.service.*;
import com.limpador.util.FormatUtils;
import com.limpador.util.PlatformUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Controller REST principal do Limpador-PC Pro.
 * Implementa coordenação centralizada de estado (AppState) para evitar conflitos concorrentes,
 * restrição de CORS para origens locais seguras e validação de escopo na limpeza.
 */
@RestController
@RequestMapping("/api")
@CrossOrigin(origins = {"http://127.0.0.1:8080", "http://localhost:8080"})
public class CleanerApiController {

    private static final Logger log = LoggerFactory.getLogger(CleanerApiController.class);

    public enum AppState {
        IDLE,
        SCANNING,
        CLEANING
    }

    private final TempScannerService tempScannerService;
    private final TrashScannerService trashScannerService;
    private final DuplicateScannerService duplicateScannerService;
    private final CleanerService cleanerService;
    private final GithubUpdateService updateService;

    // Estado único coordenado de execução
    private final AtomicReference<AppState> appState = new AtomicReference<>(AppState.IDLE);
    private final AtomicReference<String> statusMessage = new AtomicReference<>("Pronto para iniciar.");
    private final AtomicReference<ScanSummary> lastTempSummary = new AtomicReference<>(null);
    private final AtomicReference<ScanSummary> lastTrashSummary = new AtomicReference<>(null);
    private final AtomicReference<List<DuplicateGroup>> lastDuplicateGroups = new AtomicReference<>(null);
    private final List<String> logs = Collections.synchronizedList(new ArrayList<>());

    public CleanerApiController(
            TempScannerService tempScannerService,
            TrashScannerService trashScannerService,
            DuplicateScannerService duplicateScannerService,
            CleanerService cleanerService,
            GithubUpdateService updateService
    ) {
        this.tempScannerService = tempScannerService;
        this.trashScannerService = trashScannerService;
        this.duplicateScannerService = duplicateScannerService;
        this.cleanerService = cleanerService;
        this.updateService = updateService;
        addLog("Servidor Spring Boot 3 iniciado. Sistema pronto.");
    }

    private void addLog(String message) {
        String ts = java.time.LocalTime.now().format(java.time.format.DateTimeFormatter.ofPattern("HH:mm:ss"));
        String entry = "[" + ts + "] " + message;
        logs.add(entry);
        log.info(message);
        if (logs.size() > 300) {
            logs.remove(0);
        }
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getStatus() {
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("os_type", PlatformUtils.isWindows() ? "windows" : (PlatformUtils.isMac() ? "macos" : "linux"));
        resp.put("os_name", PlatformUtils.getOsDisplayName());
        resp.put("framework", "Java 21 + Spring Boot 3");
        
        AppState current = appState.get();
        resp.put("state", current.name());
        resp.put("is_scanning", current == AppState.SCANNING);
        resp.put("is_cleaning", current == AppState.CLEANING);
        resp.put("status_message", statusMessage.get());

        long totalRecoverable = 0;
        ScanSummary temp = lastTempSummary.get();
        ScanSummary trash = lastTrashSummary.get();
        List<DuplicateGroup> dups = lastDuplicateGroups.get();

        if (temp != null) totalRecoverable += temp.getTotalSize();
        if (trash != null) totalRecoverable += trash.getTotalSize();
        if (dups != null) {
            for (DuplicateGroup g : dups) {
                totalRecoverable += g.getWastedBytes();
            }
        }

        resp.put("total_recoverable", totalRecoverable);
        resp.put("total_recoverable_formatted", FormatUtils.formatSize(totalRecoverable));

        Map<String, Object> tempMap = new LinkedHashMap<>();
        tempMap.put("count", temp != null ? temp.getTotalFiles() : 0);
        tempMap.put("size", temp != null ? temp.getTotalSizeFormatted() : "0 B");
        resp.put("temp_summary", tempMap);

        Map<String, Object> recycleMap = new LinkedHashMap<>();
        recycleMap.put("count", trash != null ? trash.getTotalFiles() : 0);
        recycleMap.put("size", trash != null ? trash.getTotalSizeFormatted() : "0 B");
        resp.put("recycle_summary", recycleMap);

        Map<String, Object> dupMap = new LinkedHashMap<>();
        int dupCopies = 0;
        long dupWasted = 0;
        if (dups != null) {
            for (DuplicateGroup g : dups) {
                dupCopies += g.getCopies().size();
                dupWasted += g.getWastedBytes();
            }
        }
        dupMap.put("groups", dups != null ? dups.size() : 0);
        dupMap.put("copies", dupCopies);
        dupMap.put("wasted", FormatUtils.formatSize(dupWasted));
        resp.put("duplicate_summary", dupMap);

        resp.put("logs", new ArrayList<>(logs));
        return ResponseEntity.ok(resp);
    }

    @GetMapping("/scan/all")
    public ResponseEntity<Map<String, Object>> scanAll() {
        if (!appState.compareAndSet(AppState.IDLE, AppState.SCANNING)) {
            return ResponseEntity.badRequest().body(Map.of("error", "Uma operação já está em andamento."));
        }

        statusMessage.set("Executando varredura completa...");
        addLog("Iniciando varredura completa (Temporários, Lixeira e Duplicados)...");

        CompletableFuture.runAsync(() -> {
            try {
                statusMessage.set("Analisando Lixeira do Sistema...");
                ScanSummary trash = trashScannerService.scan();
                lastTrashSummary.set(trash);
                addLog("Lixeira: " + trash.getTotalFiles() + " itens (" + trash.getTotalSizeFormatted() + ")");

                statusMessage.set("Analisando Arquivos Temporários (%TEMP% e outros)...");
                ScanSummary temp = tempScannerService.scan();
                lastTempSummary.set(temp);
                addLog("Temporários: " + temp.getTotalFiles() + " arquivos (" + temp.getTotalSizeFormatted() + ")");

                statusMessage.set("Analisando Arquivos Duplicados com SHA-256...");
                List<DuplicateGroup> dups = duplicateScannerService.scan(null);
                lastDuplicateGroups.set(dups);
                addLog("Duplicados: " + dups.size() + " grupos encontrados.");

                statusMessage.set("Varredura finalizada! Selecione o que deseja autorizar.");
                addLog("Varredura completa concluída com sucesso.");
            } catch (Exception e) {
                statusMessage.set("Erro na varredura: " + e.getMessage());
                addLog("Erro durante a varredura: " + e.getMessage());
            } finally {
                appState.set(AppState.IDLE);
            }
        });

        return ResponseEntity.ok(Map.of("success", true, "message", "Varredura iniciada."));
    }

    @GetMapping("/scan/temp")
    public ResponseEntity<Map<String, Object>> scanTemp() {
        if (!appState.compareAndSet(AppState.IDLE, AppState.SCANNING)) {
            return ResponseEntity.badRequest().body(Map.of("error", "Uma operação já está em andamento."));
        }
        statusMessage.set("Analisando arquivos temporários...");
        addLog("Iniciando varredura de temporários...");

        CompletableFuture.runAsync(() -> {
            try {
                ScanSummary temp = tempScannerService.scan();
                lastTempSummary.set(temp);
                addLog("Temporários: " + temp.getTotalFiles() + " arquivos (" + temp.getTotalSizeFormatted() + ")");
                statusMessage.set("Varredura de temporários concluída.");
            } catch (Exception e) {
                statusMessage.set("Erro na varredura de temporários: " + e.getMessage());
                addLog("Erro: " + e.getMessage());
            } finally {
                appState.set(AppState.IDLE);
            }
        });
        return ResponseEntity.ok(Map.of("success", true));
    }

    @GetMapping("/scan/recycle")
    public ResponseEntity<Map<String, Object>> scanRecycle() {
        if (!appState.compareAndSet(AppState.IDLE, AppState.SCANNING)) {
            return ResponseEntity.badRequest().body(Map.of("error", "Uma operação já está em andamento."));
        }
        statusMessage.set("Analisando Lixeira...");
        addLog("Iniciando varredura da Lixeira...");

        CompletableFuture.runAsync(() -> {
            try {
                ScanSummary trash = trashScannerService.scan();
                lastTrashSummary.set(trash);
                addLog("Lixeira: " + trash.getTotalFiles() + " itens (" + trash.getTotalSizeFormatted() + ")");
                statusMessage.set("Varredura da lixeira concluída.");
            } catch (Exception e) {
                statusMessage.set("Erro na varredura da lixeira: " + e.getMessage());
                addLog("Erro: " + e.getMessage());
            } finally {
                appState.set(AppState.IDLE);
            }
        });
        return ResponseEntity.ok(Map.of("success", true));
    }

    @GetMapping("/scan/duplicates")
    public ResponseEntity<Map<String, Object>> scanDuplicates() {
        if (!appState.compareAndSet(AppState.IDLE, AppState.SCANNING)) {
            return ResponseEntity.badRequest().body(Map.of("error", "Uma operação já está em andamento."));
        }
        statusMessage.set("Analisando Arquivos Duplicados com SHA-256...");
        addLog("Iniciando varredura de duplicados...");

        CompletableFuture.runAsync(() -> {
            try {
                List<DuplicateGroup> dups = duplicateScannerService.scan(null);
                lastDuplicateGroups.set(dups);
                addLog("Duplicados: " + dups.size() + " grupos encontrados.");
                statusMessage.set("Varredura de duplicados concluída.");
            } catch (Exception e) {
                statusMessage.set("Erro na varredura de duplicados: " + e.getMessage());
                addLog("Erro: " + e.getMessage());
            } finally {
                appState.set(AppState.IDLE);
            }
        });
        return ResponseEntity.ok(Map.of("success", true));
    }

    @GetMapping("/details/temp")
    public ResponseEntity<Map<String, Object>> getTempDetails() {
        ScanSummary temp = lastTempSummary.get();
        if (temp == null) {
            return ResponseEntity.ok(Map.of("items", List.of(), "total_files", 0));
        }
        return ResponseEntity.ok(Map.of(
                "total_files", temp.getTotalFiles(),
                "total_size_formatted", temp.getTotalSizeFormatted(),
                "items", temp.getItems()
        ));
    }

    @GetMapping("/details/recycle")
    public ResponseEntity<Map<String, Object>> getRecycleDetails() {
        ScanSummary trash = lastTrashSummary.get();
        if (trash == null) {
            return ResponseEntity.ok(Map.of("items", List.of(), "total_items", 0));
        }
        return ResponseEntity.ok(Map.of(
                "total_items", trash.getTotalFiles(),
                "total_size_formatted", trash.getTotalSizeFormatted(),
                "items", trash.getItems()
        ));
    }

    @GetMapping("/details/duplicates")
    public ResponseEntity<Map<String, Object>> getDuplicateDetails() {
        List<DuplicateGroup> dups = lastDuplicateGroups.get();
        if (dups == null) {
            return ResponseEntity.ok(Map.of("groups", List.of()));
        }
        return ResponseEntity.ok(Map.of("groups", dups));
    }

    @PostMapping("/clean")
    public ResponseEntity<CleanResult> clean(@RequestBody CleanRequest request) {
        if (!appState.compareAndSet(AppState.IDLE, AppState.CLEANING)) {
            return ResponseEntity.badRequest().body(new CleanResult(false, 0, 0, 0, List.of("Operação em andamento. Aguarde.")));
        }

        statusMessage.set("Executando limpeza autorizada...");
        addLog("Executando limpeza autorizada pelo usuário com validação de escopo...");

        try {
            CleanResult res = cleanerService.clean(
                    request,
                    lastTempSummary.get(),
                    lastTrashSummary.get(),
                    lastDuplicateGroups.get()
            );
            for (String msg : res.getMessages()) {
                addLog(msg);
            }
            statusMessage.set("Limpeza concluída! " + res.getFreedFormatted() + " liberados.");
            addLog("Total de espaço liberado no disco: " + res.getFreedFormatted());

            // Reseta resumos para atualizar
            lastTempSummary.set(null);
            lastTrashSummary.set(null);
            lastDuplicateGroups.set(null);

            return ResponseEntity.ok(res);
        } catch (Exception e) {
            statusMessage.set("Erro durante a limpeza: " + e.getMessage());
            addLog("Erro na limpeza: " + e.getMessage());
            return ResponseEntity.internalServerError().body(new CleanResult(false, 0, 0, 0, List.of("Falha na limpeza: " + e.getMessage())));
        } finally {
            appState.set(AppState.IDLE);
        }
    }

    @GetMapping("/update/check")
    public ResponseEntity<UpdateInfo> checkUpdate(@RequestParam(required = false) String repo) {
        UpdateInfo info = updateService.checkForUpdates(repo);
        return ResponseEntity.ok(info);
    }

    @PostMapping("/update/apply")
    public ResponseEntity<Map<String, Object>> applyUpdate(@RequestBody Map<String, String> body) {
        String repo = body.get("repo");
        addLog("Iniciando auto-atualização pelo GitHub...");
        boolean ok = updateService.applyUpdate(repo);
        if (ok) {
            addLog("Atualização verificada e aplicada com sucesso a partir do branch main!");
            return ResponseEntity.ok(Map.of("success", true, "message", "Atualizado com sucesso!"));
        } else {
            addLog("Falha ao aplicar atualização do GitHub: verificação de segurança falhou ou rede indisponível.");
            return ResponseEntity.badRequest().body(Map.of("success", false, "error", "Falha na atualização de segurança."));
        }
    }

    @PostMapping("/settings")
    public ResponseEntity<Map<String, Object>> saveSettings(@RequestBody Map<String, String> body) {
        String repo = body.get("github_repo");
        if (repo != null && !repo.isBlank()) {
            boolean valid = updateService.setCurrentRepo(repo.trim());
            if (valid) {
                return ResponseEntity.ok(Map.of("success", true, "message", "Repositório configurado."));
            }
        }
        return ResponseEntity.badRequest().body(Map.of("success", false, "error", "Repositório inválido ou não autorizado."));
    }
}
