---
id: P02-3j
phase: P02
status: verified
size: M
depends_on: [P02-2c]
capabilities: [C03]
---
# P02-3j — İndirme sözleşme tipleri, doğrulama sözlüğü ve aralık sınıflandırıcısı

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 9. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md); saf mantık ve katalog, ağ/dosya sistemi yok.

## Kullanıcı sonucu ve mevcut eksik

İndirme için ortak sonuç, doğrulama seviyesi, yarım indirme durumu ve HTTP aralık yanıtı yorumu bugün yoktur. Bunlar tüketici ve aktarım kodundan önce kapalı ve test edilebilir olmazsa seviye iddiaları (“doğrulandı”) tutarsız veya fazla iddialı yazılır.

## Giren ve girmeyen kapsam

`transfer_complete`/`sha256_matched` seviyeleri ve `expectation_source` (`none|user_supplied`; `size_matched` seviyesi ve `provider_metadata`/`local_manifest` kaynakları üreten tüketici gelince eklenir); `DownloadSummary` DTO; `DownloadPartial v1` şeması (`prefix_sha256` dahil; `identity_key` hizmet hedefini — normalize origin + API kökü — de kapsar; `total_size` chunked gövdede yalnız tamamlanma checkpoint’inde kesinleşir) ve canonical kodlaması; hedef-adından kararlı kilit nesnesi/stage/sidecar/tmp adı türetimi; kapalı yanıt tablosunun saf sınıflandırıcısı ve **tipli `DownloadResponse`** ayrıştırıcısı (durum ∈ {200,206,416}, ayrıştırılmış `Content-Range`, güçlü ETag veya yok, çerçeve türü; Range’siz isteğe 206; tam-stage kısa devre satırı; gövde fazı kopma önceliği: `download_incomplete`; tablo dışı yanıtların mevcut koda eşlenmesi: diğer 2xx/`Content-Encoding` → `invalid_response`, 3xx/404/diğer 4xx → `remote_failed`); stage/sidecar başlangıç durum tablosunun (kalıntı sidecar tmp, FIFO/aygıt/sahiplik, boş stage, kesin EEXIST, hedefle aynı inode’lu artık stage, `--no-resume` kolları ve kilit-öncesi/sonrası ayrımı dahil; kilit durumu karar girdisidir) saf karar fonksiyonu; `--fold` (0–1024), `--timeout` (30–3600), `--sha256` değer alanları; 1 GiB tavan ve süre sabitleri; dokuz yeni hata kodu (`download_busy` dahil; sabit mesajlar, dosya adı/yol/URL yok) ve `download_integrity_mismatch`in kapalı ayrıntı tipi (`computed_sha256`, `bytes`) girer. Transport, dosya yazımı, motor, tüketici ve CLI girmez.

**Gerçekleşen kapsam (P02-3j).** `domain/download.py` (sınırlar ve süreler, `parse_fold`/`parse_timeout`/`parse_sha256`, `verify_expectation`, `DownloadSummary`/`DownloadSource`, `DownloadPartial v1` ve `decode`, `identity_key`, `validate_target_name`/`target_hash`/`download_names`), `domain/download_response.py` (`parse_content_range`, `parse_etag`, `parse_response` → tipli `DownloadResponse`, `ResumeAsk` ve `request_headers`, `disposition`, `check_written`/`check_body_end`/`body_failure`), `domain/download_state.py` (`decide_start`, `confirm_prefix`, `Entry`/`SidecarState`) ve `errors.py` (dokuz kod, sabit mesaj, exit eşlemesi, `DownloadIntegrityMismatch`). Kararlar: ad hash’i bayt bayt (katlama yok) ve 32 hex; boş ETag etiketi yok sayılır; başlangıç tablosu iki aşamalıdır (`decide_start` → çağıran ön eki hashler → `confirm_prefix`); sidecar’ı stage’in inode’una uymayan iz doğrulanmamıştır. Model yoklama kapısı (ADR-0032 §1) canlı girdi gerektirdiğinden **yapılmadı**: P02-3k’nin yol öneki sabiti bu karttan çıkmaz, motor loopback uyumluluğuyla teslim edilir ve tüketici “canlı doğrulanmadı” kalır. R1 sonrası eklenenler: iki aşama tipte zorunlu (`StartDecision.prefix_checked`; `confirm_prefix` silinecek tmp’yi kaybetmez, `None` yalnız yerel okuma hatasıdır), tablo karar anındaki dizine uygulanır (bu koşu stage’i yaratmadan önce; referans 5–6. adımlar buna göre yeniden yazıldı), `--no-resume` stage’i olmayan, sahipliği kanıtlı ama okunamayan sidecar’ı siler (yarım kalmış temizlik kalıcı durak olmaz), `resumable` yüklemi başlangıç ve temiz durma için tek kural, kimlik anahtarı/hedef hash’i doğrulanır, çerçevesi kurulamayan 206 ve eksik Content-Length kapalı tablodaki gibi `discard_and_retry` olur, tamamlanmış sıfır baytlık stage’in özeti temsil edilebilir, sidecar `decode` iç içe JSON’da `ValueError` verir, ayrılmış önek harf büyüklüğünden bağımsızdır, başlık alanları metin çifti olmalıdır. Testler: `tests/contracts/test_download_contract.py`, `test_download_response.py`, `test_download_state.py` (senaryo+hasar üreteçli 8.000 dizinlik kural süpürmesi, ikinci aşama, tamamlayıcılık ve her silme arasındaki kesintinin yakınsaması), `test_download_edges.py` (bağımsız mutasyon incelemesinin bulduğu sınır değerler ve kayıtlı kimlik vektörleri) ve `test_download_reference.py` (referanstaki hata tablosu ↔ kod, tel tablosunun durum satırları ↔ `parse_response`).

## Bağımlılıklar ve kararlar

[ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) Accepted’dir (2026-11-06). Sınırlar ve ad şeması burada kesinleşir; ağ davranışı P02-3k, yazıcı P02-3l’dedir. **Model yoklama kapısı bu karttan önce** yapılır (ADR-0032 §1): kullanıcının erişebildiği model sürümü ve ayrı yetkiyle tek, sınırlı, salt okuma yoklama (JSON çağrısı + ilk bayt aralığı); gözlenen tam yol öneki, Accept-Ranges/ETag/Content-Length varlığı ve durum kodu uygulama kaydına yazılır ve P02-3k’nin yol öneki sabiti bundan türetilir. Olumsuz sonuçta P02-3n yüzeysiz iç tüketici olur (P02-3o kütüphane girişini ölçer; üst kabulün canlı maddesi “oturum gerekli” kaydıyla kapanır); yoklama yapılamazsa tüketici “canlı doğrulanmadı” teslim edilir. Hata kodlarının kanonik tablosu [indirme motoru sözleşmesi](../../reference/download-engine.md) belgesindedir; CLI sözleşmesi ona bağlanır, kopyası tutulmaz.

## Sözleşme ve uygulama sınırı

Saf fonksiyonlar ve kapalı, strict, frozen, extra-forbid tipler. [indirme motoru sözleşmesi](../../reference/download-engine.md) taslağındaki alanlar burada kesinleşir. Hiç G/Ç, saat veya rastgelelik yoktur; ayrıştırıcılar girdiyi bounded okur ve bilinmeyen biçimi reddeder. Kod katalogu tek kaynakta (`errors.py` + ilgili referans) tutulur.

## Kabul

1. Seviye mantığı: beklenti kaynağı/özet kombinasyonlarının tümü için beklenen seviye ve ret (uyuşmazlık `download_integrity_mismatch`, beklentisiz “doğrulandı” yok).
2. `Content-Range` ayrıştırıcısı: geçerli, `*`, çoklu aralık, boşluk/büyük-küçük harf, taşma, başlangıç>bitiş, toplam uyuşmazlığı, negatif/aşırı büyük sayı; yanıt tablosu bağımsız vektörlerle.
3. ETag: güçlü/zayıf/boş/çok değer; yalnız güçlü ETag `If-Range` için uygun. Çerçeve: Content-Length veya chunked varsa kabul, ikisi de yoksa ret.
4. Sidecar: strict şema, ek alan/eksik alan/bool-int/boyut aşımı/yanlış sürüm reddi; canonical byte golden’ı; kilit/stage/sidecar/tmp adı uzun, Unicode ve ayrılmış adlar için sabit uzunlukta ve çakışmasız; `identity_key` farklı hizmet hedefleri (aynı sürüm UUID’si/biçim/hedef adı) için farklıdır ve uyuşmayan kimlik tam-stage dahil hiçbir resume yoluna girmez; başlangıç durum tablosunun her satırı için beklenen karar (kilit alınmadan hiçbir silme/kesme kararı çıkmaz); tam-stage satırı (`committed_bytes == total_size`) hiçbir ağ isteği (JSON çağrısı dahil) gerektirmez.
5. Hata kodları: zarf, mesaj, exit eşlemesi ve `MESSAGES` ile ilgili referans uyumu testlidir; mesajlar sabittir (dosya adı, yol, URL, ETag yok), `download_integrity_mismatch` kapalı ayrıntı taşır ve düz kod `details={}` korur (mevcut zarf testi yeşil kalır).

## Doğrulama

Unit/contract testleri, bağımsız vektörler, Ruff, strict mypy ve belge/katalog kontrolü. Ağ veya dosya sistemi davranışı iddia edilmez.

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: uygulama [cf57e55](https://github.com/HodeTech/Yorunge/commit/cf57e551616eb0d699854628122eb2292ca5e859); R1 düzeltmeleri [160d81a](https://github.com/HodeTech/Yorunge/commit/160d81a85f9bb17f34a22fc00541ea1243e01277); R2 düzeltmeleri [6e5e15e](https://github.com/HodeTech/Yorunge/commit/6e5e15e50ae4c9736e3ded772905e23064162736).
- Sonuç: İndirme sözleşme tipleri: doğrulama sözlüğü, `DownloadPartial` sidecar tipi, tipli yanıt sınıflandırıcısı ve iki aşamalı başlangıç tablosu; saftır (G/Ç yok); her tablo satırı için bağımsız vektörler, tohumlu rastgele süpürme ve yakınsama özellikleri; referansın 15 satırı koda bağlıdır (R1 ve R2 kapandı; Adım 13). Tam paket: 12.716 geçti, 1 atlandı, 0 düştü (`9ab9d6a`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Yanlış etiketli 200 yanıtlarının canlı sağlayıcıda nasıl göründüğü gözlenmedi; testler varsayımsal sunucularla yapıldı.
