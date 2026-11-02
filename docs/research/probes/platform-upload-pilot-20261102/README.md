# Tek seferlik private upload sözleşme araştırması

**Tarih:** 2026-11-02. Kullanıcı scope/tarifeyi bulamadığını, küçük denemenin yapılmasını ve başlangıçtaki 200 CR'nin aşılmasını kabul etti. Bu yürütücü o dar araştırma içindir; public ürün prepared/authority/cost-bound üretmez. Ücret/hard-cap bilinmiyor; sıfır ücret veya toplam harcama garantisi yoktur. [Yetki ve sınırlar](../../p02-2-readiness-review.md#kullanıcının-sonraki-canlı-deneme-tercihi) kanoniktir.

Tek mevcut private test projesinde bir private VISION dataset, ayrı proje bağlantısı, üç sentetik PNG (iki ad aynı içerik) ve toplam ≤1 MiB. Create/link birer; presign/PUT/confirm dosya başına en çok birer; GET en çok 10, GET physical attempt en çok 20, effectful retry sıfır, toplam 120 s ve tüketilen response body toplam 5 MiB. Proxy-only; direct URL kullanılmaz, fallback yapılmaz. Terms accept/DELETE/export/inference yoktur. Kaynak private kalır; otomatik temizlenmez.

Araştırma journal'ı Git dışındaki yeni 0700 dizinde exclusive rezerve edilir; her etkili çağrıdan önce intent fsync edilir. Aynı dizinle yeniden yürütme reddedilir; crash/cevap kaybı sonrası otomatik gönderim yoktur. Bu küçük araştırma journal'ı ürünün lease/CAS state store'u değildir; ürün recovery kabulü diye sunulmaz. Raw gövde, credential, signed URL ve object key diske yazılmaz. Dataset ID yalnız private journal'da kurtarma için tutulur; public receipt yalnız kapalı kod/sayaç/predicate taşır. Source/test commit ve SHA bağları kaydedilir; canlı koşudan sonra kaynak snapshot'ı değiştirilmez.

Provider request alanları kamu istemcisi ve SDK'daki gözlenen consumer biçimleridir. Yanıt kontrol alanları ve tüketilen ID/owner/private/filename/hash/size sıkıdır; bilinmeyen metadata seçili credential'ın mevcut literal kuralıyla tarandıktan sonra atılır. Link ve PUT yalnız boş 2xx body veya root `success=true` JSON object kabul eder; link ayrıca GET ile gözlenir. Confirm'de strict `created=1`, varsa `actual_count` o ana kadarki dosya adedi, varsa `batch_duplicates=0` zorunludur. Proxy query tam bir `key` parametresinden oluşur; strict UTF-8/tek decode değeri descriptor `object_key` ile aynı olmalıdır. Özgün query değiştirilmez; eşdeğer percent encoding tek başına ret sebebi değildir. İlk PUT'tan önce üç object key ve üç exact PUT URL tekil olmalıdır; sağlayıcının shared-key dedup anlamı bu araştırmada varsayılmaz. Bunlar temkinli araştırma oracıllarıdır, normatif provider API veya permission semantiği değildir. Schema, explicit permission reddi, wrong-parent, sınır, secret, redirect veya ilk belirsizlikte durulur. Başarısızlık yeni dataset/retry açmaz.

Kaynak/test review kapanmadan canlı giriş çağrılmaz. Çevrimdışı testler:

```sh
.venv/bin/python -m pytest docs/research/probes/platform-upload-pilot-20261102/test_pilot.py -q
```

Bu belge tek başına yeni canlı çalıştırma yetkisi değildir; ilk koşunun sonucu ve sınırlamaları araştırma kaydına ayrıca bağlanır.
