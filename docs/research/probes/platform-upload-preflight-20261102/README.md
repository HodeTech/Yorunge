# Platform upload hazırlığı için beş GET araştırma yürütücüsü

**Tarih:** 2026-11-02. Kaynak ve testler sır/hesap verisi içermez. Yürütücü yalnız kullanıcıca onaylanan beş endpoint'i sayar: me, organizations, seçilmiş proje/detail-dataset listesi, owned datasets ilk sayfası. En çok 5 GET/10 deneme/5 MiB/30 s; response başına daha dar 512 KiB. Mutasyon, billing, yanlış-key kontrolü, redirect veya raw değer yayını yoktur. Bu araç ürün veya auth/pricing kabulü değildir.

Ağsız güvenlik denetimi:

```sh
.venv/bin/python -m pytest docs/research/probes/platform-upload-preflight-20261102/test_preflight.py -q
```

Canlı yürütme girişinde açık execute flag'i, önceki özel hazırlık ve kullanıcıya ait proje ID'si gerekir. Çıktı private alanda exclusive rezerve edilir; mevcut receipt ezilmez. Kaynaklar canlı koşudan sonra hash-bound snapshot olur; sonradan değişiklik ayrı yöntem/kayıt gerektirir. Bu dosya canlı tekrar yetkisi vermez. [Kapsam ve sonuç](../../p02-2-readiness-review.md) kanoniktir.

Byte sayacı yalnız tüketilen raw response-body chunklarını ölçer; TLS/header ve okunmadan kapatılan error body bu sayıya dahil değildir. 512 KiB response alt sınırı ek güven payıdır. 30 s deadline kontrol noktaları/HTTP işlemi içindir; bloke dosya I/O/fsync/cleanup fiziksel duvar saati garantisi değildir. Exact kaynak/receipt hash bağı ve canlı koşu sonucu bağlı araştırma raporunda kaydedilir.
