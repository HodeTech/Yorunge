---
id: P02-3z
phase: P02
status: draft
size: M
depends_on: [P02-3o]
capabilities: [C03, C13]
---
# P02-3z — İndirme ölçümünün kanıt, kurulum ve CI hattı

**Tarih:** 2026-11-08. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 14 (devam); [P02-3o](p02-3o-download-native-acceptance.md)’nun ölçüm donanımından ayrıştırıldı. Büyüme kuralı P02-3l/3m ile aynıdır (s–z harfleri). Donanım (ayrı süreçte nesne sunucusu, kurulu `-I` istemcisi, kapalı `download_budget_v1` raporu) P02-3o’da; ölçümün kanıt olarak saklanması, doğrulanması, kurulu smoke’lar ve CI bu kartta.

## Kullanıcı sonucu ve mevcut eksik

Yörünge’yi kuran kişi, kurulu paketteki yeni komutların (`datasets upload resume`, `datasets versions`, `models download`) temiz bir kurulumda çalıştığına ve indirme yolunun bellek/süre kabulünün kaynağa bağlı, bağımsız doğrulanmış bir kayıtla durduğuna güvenebilmelidir. Bugün harness yalnız elle koşulabilir: raporu bağımsız yeniden hesaplayan doğrulayıcı, başarısız ölçümün tanısını saklayan kayıt, kurulu paket smoke’ları, CI orkestratörü ve workflow adımları yoktur.

## Giren ve girmeyen kapsam

Girer: (1) `scripts/download_diagnostic.py` — upload ikizinin kapalı `rejected_download_evidence_v1` kaydı: allowlist (en çok 104 ad), sembolik bağ ve sınır reddi, kayıpsız ek; (2) `research_evidence.py`: `download_budget_v1` ve `rejected_download_evidence_v1` için `typed_summary` dalları, `verify_download_reference` (kabul edilmiş rapor, ilan edilen Apple M5 Max ortamı, tam kaynak haritası ve frozen runtime eşliği), `archive-rejected-download` ve `verify-download-reference` eylemleri; (3) `benchmark-download.py` controller kancaları: `--run-url`, raporun yalnız `dist/` altında olması, kesintide `controller-error.json` + tanı saklama + yeniden fırlatma, tamamlanmış ama geçmeyen raporun arşivlenmesi (smoke alt kümelerini controller arşive almaz; elle arşivlenmiş kısmi rapor da referans kapısından geçemez); (4) `scripts/surface_installation.py` ve `scripts/download_installation.py`: kurulu `resume`, `versions` ve `models download` smoke’ları (çevrimdışı kapalı kapılar, ağ denetim kancası, loopback TLS nesne sunucusundan gerçek CLI indirmesi, harness’ın `measure_one(…, "16", 1)` yargısı); (5) `INSTALL_CHECKS_V4` / `installation_v4` (şema 4) ve `verify-distributions.py` (`--download-workspace`, wheel ve sdist için üç yeni smoke; v2 ve v3 okuyucuları değişmez); (6) `scripts/download_ci.py` (`upload_ci.py` ikizi) ve `.github/workflows/checks.yml` adımları, kanıt bağlamı çalışma alanları, artifact yolları (`evidence-artifact-paths.txt`), `CONTRIBUTING.md`, performans ve kanıt standardı bölümleri. Girmez: gerçek M5 referans ölçümü (epik sonunda, kod dondurulduktan sonra; sahibi [P02-3b](p02-3b-download-acceptance.md)), PR CI koşusu, Linux/3.14 hücrelerinin sonucu, canlı kabul.

## Bağımlılıklar ve kararlar

P02-3o (harness `49e083b`) ve upload ölçümü P02-2v. Kararlar: (a) smoke alt kümeleri (`--labels/--samples`) geçerli rapor yazar ama controller onları arşive almaz (az-etiketli alt kümede G tanımsızdır; her geliştirici smoke’u arşivlenmemeli; elle arşivlense de `accepted` olamayacağından referans kapısından geçemez); (b) kurulu smoke’ların beklenen kodları önce geliştirme ortamında çalıştırılarak bulunup sabitlenir (kartın ilk taslağı `bind --binding-out <dizin>` için `invalid_request` bekliyordu; ürün `binding_output_exists`/2 verir); (c) “ağ yok” bir test sözü değil, kurulu süreçte `socket.connect`, ad çözme ve `sendto`yu reddeden denetim kancasıyla zorlanır; (d) indirme smoke’unda sunucunun kapalı hesabı tam 1 JSON çağrısı, 1 imzalı GET ve 1 bağlantı göstermelidir (kapıların ağa dokunmadığının kanıtı); (e) `MAX_MEMBERS = 512` kanıt üyesi payı en kötü hatada 473–481’dir (kabul edildi, yükseltilmedi); boş ya da yarım `client-stdout.json` upload’daki gibi saklamayı kapalı başarısız yapar; (f) referans adı `p02-3-reference-download-1.json` ölçümden önce workflow ve testte sabittir ve henüz arşivde yoktur: `verify-download-reference` adımı o kayıt arşive girene kadar bilerek kırmızıdır.

## Sözleşme ve uygulama sınırı

[Kanıt standardı](../../standards/research-evidence.md) (“Download budget evidence v1”, “Rejected download evidence v1”, “Installation evidence v4 ve download CI”) ve [performans standardı](../../standards/performance.md#kurulu-indirme-ölçümü) kanoniktir; kart ikinci sözleşme tanımlamaz. Üretim kodu (`src/`) değişmez; harness dosyalarının değişimi yalnız controller kancalarıdır.

## Kabul

1. `verify-download-reference` kabul edilmiş raporu bağımsız yeniden hesaplar; eksik, eski, yabancı ortam, başka kaynak haritası, başka kilit ve değiştirilmiş rapor kapalı kodla reddedilir; mevcut verifier’lar etkilenmez (testli: 53 test, 27 kural reddi ve arşiv bozma vakaları).
2. Başarısız ya da kesilen ölçümün özgün çıktıları kayıpsız saklanır (`rejected_download_evidence_v1`: sınırlar, yalanlar, sembolik bağlar, gizlilik kapısı); başarısız örnek silinmez, en iyi koşu seçilmez.
3. Kurulu wheel ve sdist’te `resume_smoke`, `versions_smoke` ve `download_smoke` geçer; bozuk ürün (yanlış kod, ağa uzanan kapı, yanlış bayt) smoke’u kırar ve özgün çıktılar saklanır; `installation_v4` kayıtları v2/v3 arşivlerini bozmaz.
4. `download_ci.py` gerçek 12 işçili controller’ı sahipli süreç grubunda koşturur, `validate_output` kabul + aynı commit/ortam/runtime + güncel kaynak haritasını ister; workflow geçerlidir (actionlint), adımlar ve artifact yolları sözleşme testiyle sabittir.
5. Altı temiz kurulum ve üç ortam CI koşusu PR aşamasında ve referans kaydı arşive girdikten sonra kontrol edilir; bu kart bunu iddia etmez.

## Doğrulama

Sözleşme testleri (bu kartın 8 yeni dosyası), mutasyon özdenetimi, actionlint, Ruff, strict mypy, belge ve ajan rehberi denetimi; kurulu wheel üzerinde gerçek smoke’lar ve `verify-distributions.py` tam koşusu; gerçek 12 işçili `download_ci.py` koşusu (referans değil, zincirin uçtan uca kanıtı). Eşzamanlı ağır iş olmadan ölçülen hiçbir değer iddia edilmez.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı henüz bu alana işlenmedi.
