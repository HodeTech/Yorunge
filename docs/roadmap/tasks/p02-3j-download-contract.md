---
id: P02-3j
phase: P02
status: draft
size: M
depends_on: [P02-2c]
capabilities: [C03]
---
# P02-3j — İndirme sözleşme tipleri, doğrulama sözlüğü ve aralık sınıflandırıcısı

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 9. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md); saf mantık ve katalog, ağ/dosya sistemi yok.

## Kullanıcı sonucu ve mevcut eksik

İndirme için ortak sonuç, doğrulama seviyesi, yarım indirme durumu ve HTTP aralık yanıtı yorumu bugün yoktur. Bunlar tüketici ve aktarım kodundan önce kapalı ve test edilebilir olmazsa seviye iddiaları (“doğrulandı”) tutarsız veya fazla iddialı yazılır.

## Giren ve girmeyen kapsam

`transfer_complete`/`sha256_matched` seviyeleri ve `expectation_source` (`none|user_supplied`; `size_matched` seviyesi ve `provider_metadata`/`local_manifest` kaynakları üreten tüketici gelince eklenir); `DownloadSummary` DTO; `DownloadPartial v1` şeması (`prefix_sha256` dahil) ve canonical kodlaması; hedef-adından kararlı stage/sidecar adı türetimi; kapalı yanıt tablosunun saf sınıflandırıcısı ve **tipli `DownloadResponse`** ayrıştırıcısı (durum ∈ {200,206,416}, ayrıştırılmış `Content-Range`, güçlü ETag veya yok, çerçeve türü; Range’siz isteğe 206; tam-stage kısa devre satırı; gövde fazı kopma önceliği: `download_incomplete`); stage/sidecar başlangıç durum tablosunun (kalıntı sidecar tmp, FIFO/aygıt/sahiplik, boş stage, kesin EEXIST dahil) saf karar fonksiyonu; `--fold` (0–1024), `--timeout` (30–3600), `--page`, `--sha256` değer alanları; 1 GiB tavan ve süre sabitleri; sekiz yeni hata kodu girer. Transport, dosya yazımı, motor, tüketici ve CLI girmez.

## Bağımlılıklar ve kararlar

[ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)’nin Accepted olması gerekir (bugün Proposed). Sınırlar ve ad şeması burada kesinleşir; ağ davranışı P02-3k, yazıcı P02-3l’dedir. **Model yoklama kapısı bu karttan önce** yapılır (ADR-0032 §1): kullanıcının erişebildiği model sürümü ve ayrı yetkiyle tek, sınırlı, salt okuma yoklama (JSON çağrısı + ilk bayt aralığı); gözlenen tam yol öneki, Accept-Ranges/ETag/Content-Length varlığı ve durum kodu uygulama kaydına yazılır ve P02-3k’nin yol öneki sabiti bundan türetilir. Olumsuz sonuçta P02-3n yüzeysiz iç tüketici olur (P02-3o kütüphane girişini ölçer; üst kabulün canlı maddesi “oturum gerekli” kaydıyla kapanır); yoklama yapılamazsa tüketici “canlı doğrulanmadı” teslim edilir. Hata kodlarının kanonik tablosu [indirme motoru sözleşmesi](../../reference/download-engine.md) belgesindedir; CLI sözleşmesi ona bağlanır, kopyası tutulmaz.

## Sözleşme ve uygulama sınırı

Saf fonksiyonlar ve kapalı, strict, frozen, extra-forbid tipler. [indirme motoru sözleşmesi](../../reference/download-engine.md) taslağındaki alanlar burada kesinleşir. Hiç G/Ç, saat veya rastgelelik yoktur; ayrıştırıcılar girdiyi bounded okur ve bilinmeyen biçimi reddeder. Kod katalogu tek kaynakta (`errors.py` + ilgili referans) tutulur.

## Kabul

1. Seviye mantığı: beklenti kaynağı/özet kombinasyonlarının tümü için beklenen seviye ve ret (uyuşmazlık `download_integrity_mismatch`, beklentisiz “doğrulandı” yok).
2. `Content-Range` ayrıştırıcısı: geçerli, `*`, çoklu aralık, boşluk/büyük-küçük harf, taşma, başlangıç>bitiş, toplam uyuşmazlığı, negatif/aşırı büyük sayı; yanıt tablosu bağımsız vektörlerle.
3. ETag: güçlü/zayıf/boş/çok değer; yalnız güçlü ETag `If-Range` için uygun. Çerçeve: Content-Length veya chunked varsa kabul, ikisi de yoksa ret.
4. Sidecar: strict şema, ek alan/eksik alan/bool-int/boyut aşımı/yanlış sürüm reddi; canonical byte golden’ı; stage/sidecar adı uzun, Unicode ve ayrılmış adlar için sabit uzunlukta ve çakışmasız; başlangıç durum tablosunun her satırı için beklenen karar; tam-stage satırı (`committed_bytes == total_size`) GET gerektirmez.
5. Hata kodları: zarf, mesaj, exit eşlemesi ve `MESSAGES` ile ilgili referans uyumu testlidir.

## Doğrulama

Unit/contract testleri, bağımsız vektörler, Ruff, strict mypy ve belge/katalog kontrolü. Ağ veya dosya sistemi davranışı iddia edilmez.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
