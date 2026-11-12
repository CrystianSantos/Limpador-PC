package com.limpador;

import com.limpador.model.CleanRequest;
import com.limpador.model.CleanResult;
import com.limpador.model.DuplicateGroup;
import com.limpador.model.FileItem;
import com.limpador.model.ScanSummary;
import com.limpador.service.CleanerService;
import com.limpador.service.DuplicateScannerService;
import com.limpador.service.GithubUpdateService;
import com.limpador.service.TempScannerService;
import com.limpador.service.TrashScannerService;
import com.limpador.util.FormatUtils;
import com.limpador.util.PlatformUtils;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("Suíte de Testes Automatizados - Limpador-PC Pro")
public class LimpadorApplicationTests {

    @Test
    @DisplayName("Teste de Formatação de Tamanho em Bytes")
    void testFormatUtils() {
        assertEquals("0 B", FormatUtils.formatSize(0));
        assertEquals("500 B", FormatUtils.formatSize(500));
        assertEquals("1.0 KB", FormatUtils.formatSize(1024));
        assertEquals("5.00 MB", FormatUtils.formatSize(5 * 1024 * 1024));
        assertEquals("2.00 GB", FormatUtils.formatSize(2L * 1024 * 1024 * 1024));
    }

    @Test
    @DisplayName("Teste de Detecção de Plataforma e Diretórios do Sistema")
    void testPlatformUtils() {
        assertNotNull(PlatformUtils.getOsDisplayName());
        Map<String, Path> safeDirs = PlatformUtils.getSafeTempDirectories();
        assertNotNull(safeDirs);
        assertFalse(safeDirs.isEmpty(), "Deveria encontrar ao menos uma pasta temporária segura no sistema");
    }

    @Test
    @DisplayName("Teste de Detecção de Duplicados em 3 Fases (SHA-256)")
    void testDuplicateScannerService(@TempDir Path tempDir) throws IOException {
        Path f1 = tempDir.resolve("original.txt");
        Path f2 = tempDir.resolve("copia1.txt");
        Path f3 = tempDir.resolve("unico.txt");

        byte[] dupContent = "Conteúdo idêntico para teste de arquivos duplicados em Java.".repeat(30).getBytes();
        byte[] uniqueContent = "Conteúdo único e totalmente diferente para validação.".repeat(30).getBytes();

        Files.write(f1, dupContent);
        Files.write(f2, dupContent);
        Files.write(f3, uniqueContent);

        DuplicateScannerService scanner = new DuplicateScannerService();
        List<DuplicateGroup> groups = scanner.scan(List.of(tempDir));

        assertEquals(1, groups.size(), "Deveria encontrar exatamente 1 grupo de arquivos duplicados");
        DuplicateGroup group = groups.get(0);
        assertNotNull(group.getOriginal());
        assertEquals(1, group.getCopies().size(), "Deveria identificar 1 cópia");
        assertEquals(group.getFileSize(), group.getWastedBytes(), "Espaço desperdiçado calculado corretamente");
    }

    @Test
    @DisplayName("Teste do Serviço de Varredura de Temporários")
    void testTempScannerService() {
        TempScannerService service = new TempScannerService();
        ScanSummary summary = service.scan();

        assertNotNull(summary);
        assertNotNull(summary.getTitle());
        assertTrue(summary.isSafeToDelete());
    }

    @Test
    @DisplayName("Teste do Serviço de Varredura de Lixeira")
    void testTrashScannerService() {
        TrashScannerService service = new TrashScannerService();
        ScanSummary summary = service.scan();

        assertNotNull(summary);
        assertNotNull(summary.getTitle());
        assertTrue(summary.isSafeToDelete());
    }

    @Test
    @DisplayName("CleanerService preserva temporários fora do escopo autorizado")
    void testCleanerServicePreservesFilesOutsideApprovedTempRoots(@TempDir Path tempDir) throws IOException {
        Path tempFile = tempDir.resolve("lixo_temporario.tmp");
        Files.write(tempFile, "dados que podem ser apagados".getBytes());

        FileItem item = new FileItem(
                tempFile.toAbsolutePath().toString(),
                "lixo_temporario.tmp",
                "Temp",
                Files.size(tempFile),
                "12/11/2026 12:00:00",
                false,
                true
        );

        ScanSummary tempSummary = new ScanSummary(
                "Teste",
                1,
                Files.size(tempFile),
                "Teste",
                true,
                List.of(item)
        );

        CleanRequest req = new CleanRequest();
        req.setAuthTemp(true);
        req.setAuthRecycle(false);
        req.setAuthDuplicates(false);

        CleanerService cleaner = new CleanerService();
        CleanResult result = cleaner.clean(req, tempSummary, null);

        assertTrue(result.isSuccess());
        assertEquals(0, result.getDeletedCount());
        assertEquals(1, result.getSkippedCount());
        assertTrue(Files.exists(tempFile), "Arquivo fora das pastas temporárias autorizadas deve ser preservado");
    }

    @Test
    @DisplayName("Teste de Configuração e URL do Repositório GitHub")
    void testGithubUpdateService() {
        GithubUpdateService updateService = new GithubUpdateService();
        assertEquals("CrystianSantos/Limpador-PC", updateService.getCurrentRepo());
        updateService.setCurrentRepo("novo-dono/novo-repo");
        assertEquals("novo-dono/novo-repo", updateService.getCurrentRepo());
    }
}
