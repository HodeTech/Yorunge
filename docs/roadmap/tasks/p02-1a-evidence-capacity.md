---
id: P02-1a
phase: P02
status: verified
size: M
depends_on: [P02-0]
capabilities: [C13]
---
# P02-1a — Sınırlı araştırma kanıtı kapasitesi

**Tarih:** 2026-11-01. [Paket/adım 1](../p02-1-delivery-plan.md), [B15](../backlog.md). Bu kart ürün manifesti değildir; araştırma kanıtı altyapısını sahiplenir.

## Kullanıcı sonucu ve mevcut eksik

Reviewer bütün önceki başarısız ve başarılı ölçümleri kayıpsız inceleyebilir; yeni P02-1 ölçümleri kapasite yüzünden saklanamadan kalmaz. Katalog 247/256 kayıtta; mevcut per-file sınırları yanında bütün katalog için toplam byte sınırı yoktur.

## Giren ve girmeyen kapsam

Aynı evidence schema 1, CLI/ad/path/anchor ve özetleri korunarak en çok 4.096 kayıt; toplam gzip 128 MiB ve açılmış özgün içerik 512 MiB. Mevcut rapor 16 MiB, gzip 4 MiB, manifest/indeks 16 MiB değişmez. Okuma tek raporla sınırlı kalır. Yazı öncesi sayı/byte/üretilen metadata preflight’ı ve gerçek verifier denetimi eklenir. Bölümleme, eski kayıt silme/yeniden serileştirme, yeni arşiv deposu veya performans/ADR-0019 kapısı gevşetme yoktur.

## Bağımlılıklar ve kararlar

P02-0 ve bütün alt kabuller [PR #12 / merge 9f30fd2](https://github.com/HodeTech/Yorunge/pull/12) ile tamamdır; [merge kanıtı](../../research/p02-0-implementation-validation.md#development-merge-kapanışı). B15 bakım seçimi paket planındadır; şema veya saklama anlamı değişmediğinden yeni ADR gerektirmez. Bu bağımsız script işi ADR-0023 ürün onayını beklemez. Nihai kaynak bağlı ölçümden önce bitmelidir.

## Sözleşme ve uygulama sınırı

`scripts/research_evidence.py`, gerçek tüketici testleri ve [kanıt standardı](../../standards/research-evidence.md). Manifestte boyut sayaçları strict int, bool/float değil; ilan edilen toplamlar preflight’tır, gerçek gzip/decoded byte/hash doğrulamasının yerine geçmez. Aday dahil bütün mevcut katalog/indeks arşiv bütünlüğü yeni yazıdan önce doğrulanır. Metadata byte tavanları yeni yazı başlamadan kodlanmış gerçek baytlarda kontrol edilir.

## Kabul

1. 256’dan sonraki kayıt eklenir; eski 247 gzip/entry/anchor baytları/özgün hash ve geçmiş başarısız/tanı anlamları korunur. Aynı ismi ezme veya eksik/orphan/stale katalog üzerine yeni başarı yoktur.
2. Sayı, toplam gzip/decoded ve metadata tavanları için sınır−1/sınır/sınır+1; limit reddinde gzip/manifest/indeks ve girdi tamamen değişmeden kalır. Küçük sentetik limitlerle bütün dallar, gerçek sabitlerle 257 ve 4.096 kayıt yapısı ayrıca doğrulanır; salt duplicate kayıtla dolu katalog geçmez.
3. Sahte düşük boyut, bool/float/negatif sayaç, bozuk gzip, gzip bombası ve toplam gerçek tüketim kontrollü reddedilir. Doğrulama bütün decoded raporları aynı anda tutmaz. Mevcut per-file byte korumaları parse öncesi kalır; post-parse kontrol parser allocation garantisi diye sunulmaz.
4. Metadata replace/gzip write hatası ve kesintide kaynak korunur; orphan/eski indeks `verify` ile reddedilir. Üç dosyanın birlikte transaction olduğu iddia edilmez; kota preflight reddi ile I/O kesintisi farklı kabul edilir.
5. `show` eski baytları döndürür, iki kaynak reference verifier eski adları bulur fakat yeni script/test kaynağı için eski referansı doğru biçimde reddeder; script/test değişikliği eski M5 referansını yeni kaynak kabulü yapmaz. Fresh referanslar final adımda alınır.
6. Yoğun sentetik katalogda süre/native RSS ve gerçek 247 arşiv doğrulaması kaydedilir. Fiziksel katı süre taahhüdü yoktur; toplam byte/adet sonlu, raporlar seri açılır. Raw açılımları reviewer bağlamına dökülmez.

## Doğrulama

Araç contract testleri, format/lint, belge/ajan ve gerçek arşiv eşliği; değişen kaynak map’i nedeniyle nihai startup/jobs ölçümü P02-1 kapanışında yenilenir. Yeni gerçek ölçüm eski kaynakla uyumluymuş gibi gösterilmez. Her adım için commit ve iki fresh review turu [uygulama kaydına](../../research/p02-1-implementation-validation.md) yazılır.

## Teslim kaydı

- PR/commit: [694a7b7](https://github.com/HodeTech/Yorunge/commit/694a7b7), [b301682](https://github.com/HodeTech/Yorunge/commit/b301682), [ec40164](https://github.com/HodeTech/Yorunge/commit/ec40164); [PR #13](https://github.com/HodeTech/Yorunge/pull/13), **2026-11-02 12:33:51 Europe/Istanbul** tarihinde [50d68b1](https://github.com/HodeTech/Yorunge/commit/50d68b1deab80d6fe14749d556efde1f103b5759) ile development’a teslim edildi; [merge/CI kaydı](../../research/p02-1-implementation-validation.md#development-merge-kapanışı).
- Sonuç: [İki fresh kod turu, iki ek fresh teyit ve kapanış kanıtı](../../research/p02-1-implementation-validation.md#p02-1a-kapanışı--yerel-ve-bağımsız-bakım). 425 ilgili test, format/lint/mypy, 247 eski entry/arşiv byte eşliği ve adım kabulündeki 248 arşivin verifier denetimi geçti. 256→257 ve gerçek 4.096 kayıt kapasitesi üç fresh süreçli yoğun profilde doğrulandı; raw/decoded read-ahead P2’leri gerçek sayaç regresyonlarıyla kapatıldı.
- Kalan sınır: Bu yalnız B15 bakım kabulüdür. Ürün manifest/scan/CLI, tam paket/CI ve fresh kaynak bağlı startup/jobs, aynı pakette P02-1d kabulüyle ayrıca tamamlandı; eski kaynak referansları bilinçli reddedilir. Üç dosyanın I/O kesintisinde birlikte transaction olduğu iddia edilmez.
