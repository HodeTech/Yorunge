---
id: P02-3o
phase: P02
status: draft
size: M
depends_on: [P02-3n]
capabilities: [C03, C13]
---
# P02-3o — İndirme native ölçümü, kanıt doğrulayıcısı ve kurulu smoke

**Tarih:** 2026-11-06; bölünme 2026-11-08. Büyüme kuralı P02-3l/3m ile aynıdır (ölçüm/doğrulayıcı/CI ayrı birimlere bölünebilir; s–z harfleri): **ölçüm donanımı ve kapalı rapor bu kartta kaldı; doğrulayıcı, tanı saklama, kurulu smoke ve CI [P02-3z](p02-3z-download-evidence-installation-ci.md)’ye ayrıldı.** [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 14. Aktarım kabulü gerçek indirme yolunda 16/256/1.024 MiB ölçülür ([performans standardı](../../standards/performance.md)).

## Kullanıcı sonucu ve mevcut eksik

Mevcut ham akış ölçümü diske yazmaz ve upload ölçümü indirmeyi kapsamaz. İndirme yolu için bellek/süre ve doğruluk kabulü yoktur.

## Giren ve girmeyen kapsam

`benchmark-download.py`, Range/ETag destekli ölçüm sunucusu fixture’ı (P02-3n yüzeysizse kütüphane girişini ölçer), native RSS B/H0/H1 yöntemi (disk yazımı, checkpoint `os.fsync` sayısı/süresi ve yayın `full_sync` süresi pencere içinde ve ayrı kaydedilir), indirme kanıt özeti/rapor türü ve `research_evidence.py verify-download-reference`, M5 çalışma zamanı kapısı ve kaynak-haritası eşliği, `evidence_privacy` bağlam eklemeleri, kalıcı arşiv girişi, kurulu smoke (installation kaydının genişletilmesi), CI iş akışı adımı ve performans standardı/CONTRIBUTING güncellemeleri girer. Upload veya raw stream ölçümlerinin değiştirilmesi girmez. Bölünme: bu kart `benchmark-download.py`, ölçüm sunucusu/istemcisi, B/H0/H1 yöntemi, sayaçlar ve kapalı `download_budget_v1` raporunu (bağımsız oracle’lı 27 adlı kural) kapsar; `verify-download-reference`, `evidence_privacy` bağlamı, arşiv girişi, kurulu smoke, CI adımı ve standart/CONTRIBUTING güncellemeleri P02-3z’dedir.

## Bağımlılıklar ve kararlar

P02-3n verified olmalıdır. Ölçüm kuralları standarttadır (U≤64 MiB, G≤8 MiB, ayrı kurulu `-I` süreç, seri, başarısız örnek saklama). Kaynak bağlı M5 referansı yalnız referans host’ta alınır; Linux koşusu CI’da kabul edilmemişse işi kırar (zorunlu kapı) ama M5 referansının yerine geçmez. ADR-0030 hâlâ Proposed olsa da bu referans mevcut kurallarla alınır; ADR-0030 kararı P02-7 öncesine kadar beklemeyi sürdürür. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) kabul bölümü kaynaktır.

## Sözleşme ve uygulama sınırı

Ölçüm istemcisi kurulu paketteki gerçek indirme kodunu kullanır; sunucu ayrı süreçtir ve sunucu RSS’i eklenmez. Bayt/SHA-256, istek/bağlantı sayıları, disk yazımı (sayı, bayt, süre), stage `fsync` ve yayın `full_sync` sayı/süreleri ve native sayaç birimleri kayıtlıdır (link süresi ayrıca ölçülmez). Kayıt kapalı bir kanıt biçiminde arşivlenir; mevcut referans ve arşivler ezilmez. CI’da 1 GiB diske yazan indirme ölçülebilir (mevcut raw stream emsali); native referans M5’e özeldir.

## Kabul

(1–2 bu karttadır ve donanımın mekaniğini sınar; ölçülen değerler epik sonunda sessiz referans makinesinde alınır. 3–5 [P02-3z](p02-3z-download-evidence-installation-ci.md)’dedir.)

1. 16/256/1.024 MiB için her boyutta bağımsız oracle ile bayt/SHA eşleşir, U≤64 MiB ve boyutlar arası G≤8 MiB sağlanır; başarısız örnekler saklanır, eşik yükseltilmez.
2. Kesik+devam senaryosu ölçülür ve hash doğrudur.
3. `verify-download-reference` kayıtlı kaynak/kurulum/fixture eşliğini ve eksik/eski/yabancı ortam retlerini doğrular; mevcut verifier’lar etkilenmez.
4. Altı temiz kurulumda kurulu CLI indirme smoke’u çalışır; actionlint ve CI tanımı geçerlidir; `evidence_privacy` bağlamı ve arşiv girişi doğrulanır.
5. Sonuçlar [kanıt standardına](../../standards/research-evidence.md) göre kalıcı arşive girer; CI koşusu PR aşamasında üç ortamda kontrol edilir.

## Doğrulama

Native ölçüm betiği, kanıt doğrulayıcısı ve contract testleri, kurulum/dağıtım denetimi, belge kontrolü, actionlint, Ruff, strict mypy. Eşzamanlı ağır iş olmadan seri ölçüm.

**P02-3m devri (yazma maliyeti).** Motor her TLS kaydını (≤16 KiB) gelir gelmez yazar. Yüklü bir ana bilgisayarda küçük yazmalar pahalı ölçüldü (4–16 KiB yazma başına 1–3 ms ≈ birkaç MB/s; 1 MiB yazmalar ≈ 190 MB/s; sessiz makinede ölçülmedi). Bu kartın ölçümü motorun gerçek hızını ve yazma başına maliyeti sessiz makinede kaydeder; bütçe tutmazsa kaldıraç, çalışan olay döngüsü turunda zaten gelmiş kayıtları (araya `await` girmeden) birleştirip tek `write` yapmaktır — kayıt başına yazma ve “her kayıt bir sonrakini beklemeden yazılır” ilkesi o zaman gerekçesiyle değiştirilir, sessizce değil.

**Gerçekleşen kapsam (P02-3o).** `tests/fixtures/download_native_data.py` (etiketler `16/256/1024/resume` ve ısınma `warm`/`warm-resume`; nesne baytı `p` = `(p + 37·(p>>16)) % 256`, 64 KiB bloklar, desen 16 MiB’da bir tekrarlar; üç bağımsız türetim: oracle `bytes.translate`, sunucu 256 baytlık döngüyü döndürüp tekrarlar, doğrulayıcı periyodik tampon üzerinde pencere kaydırır; `RESUME_CUT_AT = 24·8 MiB + 1.000.003`), `download_native_server.py` (ayrı süreç, yalnız stdlib TLS; JSON çağrısı tam `X-API-Key` ister, imzalı hedef yol+ham sorguyla eşleşmelidir, imzalı GET’te kimlik ya da kapalı listenin dışında başlık 403/400 ve hesapta kayıt; `Range: bytes=N-` 206, bayat `If-Range` tam 200, `N ≥ boyut` 416; kesik etiketin ilk GET’i dürüst başlığı gönderip `cut_at` baytta kapanır; ≤ 64 KiB yazma, kapalı kanonik JSON hesabı), `download_native_control.py`, `download_native_client.py` (kurulu `python -I -W error` işçisi: ısınma, B, H0, pencere = gerçek `api.download_model_weights(sha256=oracle)` çağrı(ları), hemen H1; pencere içinde stage `os.write`, `os.fsync` ve yayın `full_sync` çağrıları sayılır ve süreleri toplanır — `instrumented: true`, ek yük raporda açık; doğrulama ve dizin içeriği pencere dışında), `scripts/download_evidence.py` (27 adlı kural: `rss_upper`, `window_seconds`, `result_*`, `directory_clean`, `write_accounting`, `write_block`, `checkpoint_fsyncs`, `full_sync`, `warm_result`, `server_*` ve `warm_server_*` × 7; `growth` yalnız **farklı bayt etiketleri** arasında; `accepted = passed and not partial`; kaynak haritası ortak startup haritası + upload vektörü) ve `scripts/benchmark-download.py` (12 seri işçi, `open("xb")` ile bir kez yazılan rapor, işçi başarısızlığında özgün dosyalar ve `controller-error.json`, çıkış 0 yalnız `accepted` iken). Testler: `tests/contracts/test_download_native.py` (66) ve `test_download_evidence.py` (329: guard testleri `judge_run`ı doğrudan çağırır); implementer’ın 131 mutantlık özdenetimi 131/131 öldü (`max(0, …)` yalnız geçerli veride eşdeğer). Kararlar: yayın `full_sync`i iki kez çağırır (`download_sink.publish` ve `ArtifactPublisher._finalize`) — harness 1–2’yi kabul eder; 4–16 KiB yazma maliyeti (P02-3m devri) bu kartta ölçülmez, **kanıtı toplanır** (sayaçlar); kayıtları birleştirme kararı sessiz makinede alınmış ölçümle verilir ve bu kartta verilmedi. **Yapılmadı:** referans ölçümü (epik sonu, kod donduktan sonra, sessiz Apple M5 Max), Linux/3.14 ve macOS CI hücreleri (harness yalnız Darwin/3.11’de koşuldu), canlı kabul.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
