# Araç sağlayıcısı sözleşmesi

**Durum:** Tasarlanan v1 port; henüz Python arayüzü yok. **Tarih:** 2026-10-27.

## Mantıksal portlar

| İşlem | Girdi / çıktı | Güvence |
|---|---|---|
| `describe` | Kimlik, sürüm aralığı, task/model/format yetenek manifesti | Ağır araç import veya gizli kurulum yapmaz |
| `check` | Executable/env ve sürüm → uyum/eksik önkoşul | Kullanıcının açık tanılama niyeti; bounded süre |
| `prepare` | TaskSpec + context + execution → ToolPlan | Dönüşüm/kayıp raporu; eğitim/uzak yan etki başlatmaz |
| `validate` | Plan + güncel environment → geçerlilik | Destek ve kritik girdi değişimini yakalar |
| `collect` | Execution sonucu → typed artefakt/metrik tanımları | Başarı koduna rağmen eksik sonucu yakalar |

`ExecutionBackend` ayrı portta `start`, `status`, `cancel`, `reconcile`, `fetch` işlemlerini uygular. Araç adaptörü hangi komut/veri biçiminin gerektiğini hazırlar; ortam bunları nerede/hangi kaynakla çalıştırdığını sahiplenir. Yönetilen EVREN servisi özel hizmet backend'i kullanabilir; her görev haricî araca zorlanmaz.

## ToolPlan

Şema sürümü, task kimliği, tool id/sürüm/executable kimliği, execution hedefi, girdi hash/sürüm bağları, argv, çalışma dizini, gerekli env/secret **referansları**, beklenen artefakt rolleri, deadline ve izin gereksinimleri bulunur. Planda ham credential veya shell string bulunmaz. Execution identity ve güvenlik politikasıyla karşılaştırılmadan çalıştırılmaz.

ToolPlan, [üst planın hizmet ve yetki bağlarına](../architecture/execution-model.md#planın-içerdiği-bağlar) tabidir. Env/secret referansları bu bağların yerine geçmez; aracın kullanacağı hedef ve sır da doğrulanmış bağla eşleşmelidir.

Görevler `llm.data.ingest`, `llm.data.audit`, `llm.data.generate`, `llm.fit.check`, `llm.train`, `llm.evaluate`, `llm.merge`, `llm.export` gibi anlamlı kimliklerle kaydedilir. Bu görevlerde desteklenen ForgeLM yetenekleri varsayılan, muadiller görev bazında seçilebilir olur. EVREN native `dataset.upload` veya `vision.train.managed` ayrı hizmet görevleridir. Yalnız uygulanıp doğrulanan görev manifestte kullanılabilir görünür; diğerleri plan olarak kalır.

## Eşleme ve sonuç

Ortak alanın desteklenmemesi açık validation hatasıdır. Açıkça kayıplı dönüştürme gerekiyorsa kayıp/alternatif kullanıcıya plan öncesinde gösterilir ve kabul edilen plan bunu kaydeder. Araç özel parametreler korunur; “muadil” bütün davranışların eşitliği değildir.

Sonuç; provider run id/exit code, normalize execution durumu, tipli metrikler, artefakt rolleri, uyarılar ve doğrulama seviyesini içerir. Cancellation veya exit 0, içerik teslimini tek başına kanıtlamaz. Değerlendirme onay bekliyorsa bunu op durumuna anlamlı eşler.

## Adaptör kabulü

Desteklenen sürüm/görev matrisi, sentetik ortak contract suite, en az bir gerçek süreç sınırı, iptal/deadline, eksik çıktı, sır sızıntısı ve tekrar başlatma deneyleri gerekir. EVREN runtime desteği bu testlerden ayrıca execution erişim kapısına bağlıdır. İlk teslimde ForgeLM + en az bir muadil aynı task/çıktı sınıfıyla doğrulanır; yalnız iki farklı komut çalıştırmak yeterli değildir.
