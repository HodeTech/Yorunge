---
id: P02-3j
phase: P02
status: draft
size: M
depends_on: [P02-2f]
capabilities: [C03]
---
# P02-3j — İndirme sözleşme tipleri, doğrulama sözlüğü ve aralık sınıflandırıcısı

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 7. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md); saf mantık ve katalog, ağ/dosya sistemi yok.

## Kullanıcı sonucu ve mevcut eksik

İndirme için ortak sonuç, doğrulama seviyesi, yarım indirme durumu ve HTTP aralık yanıtı yorumu bugün yoktur. Bunlar tüketici ve aktarım kodundan önce kapalı ve test edilebilir olmazsa seviye iddiaları (“doğrulandı”) tutarsız veya fazla iddialı yazılır.

## Giren ve girmeyen kapsam

`transfer_complete`/`size_matched`/`sha256_matched` seviyeleri ve `expectation_source`; `DownloadSummary` DTO; `DownloadPartial v1` şeması ve canonical kodlaması; hedef-adından kararlı stage/sidecar adı türetimi; `Content-Range`, `ETag` gücü ve 200/206/416 yanıt sınıflandırması; 1 GiB tavan ve süre sabitleri; yedi yeni hata kodu (katalog, mesaj, exit, CLI tablosu) girer. Transport, dosya yazımı, motor, tüketici ve CLI girmez.

## Bağımlılıklar ve kararlar

[ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) onayı gerekir. Sınırlar ve ad şeması burada kesinleşir; ağ davranışı P02-3k, yazıcı P02-3l’dedir.

## Sözleşme ve uygulama sınırı

Saf fonksiyonlar ve kapalı, strict, frozen, extra-forbid tipler. [indirme motoru sözleşmesi](../../reference/download-engine.md) taslağındaki alanlar burada kesinleşir. Hiç G/Ç, saat veya rastgelelik yoktur; ayrıştırıcılar girdiyi bounded okur ve bilinmeyen biçimi reddeder. Hata katalogları tek kaynakta (`errors.py`, CLI hata tablosu) tutulur.

## Kabul

1. Seviye mantığı: beklenti kaynağı/özet/boyut kombinasyonlarının tümü için beklenen seviye ve ret (uyuşmazlık `download_integrity_mismatch`, beklentisiz “doğrulandı” yok).
2. `Content-Range` ayrıştırıcısı: geçerli, `*`, çoklu aralık, boşluk/büyük-küçük harf, taşma, başlangıç>bitiş, toplam uyuşmazlığı, negatif/aşırı büyük sayı; 200/206/416 ve diğer durumlar için karar tablosu bağımsız vektörlerle.
3. ETag: güçlü/zayıf/boş/çok değer; yalnız güçlü ETag `If-Range` için uygun.
4. Sidecar: strict şema, ek alan/eksik alan/bool-int/boyut aşımı/yanlış sürüm reddi; canonical byte golden’ı; stage/sidecar adı uzun, Unicode ve ayrılmış adlar için sabit uzunlukta ve çakışmasız.
5. Hata kodları: zarf, mesaj, exit eşlemesi ve `MESSAGES` ile CLI kataloğu uyumu testlidir.

## Doğrulama

Unit/contract testleri, bağımsız vektörler, Ruff, strict mypy ve belge/katalog kontrolü. Ağ veya dosya sistemi davranışı iddia edilmez.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
