---
id: P02-2l
phase: P02
status: verified
size: M
depends_on: [P02-2k]
capabilities: [C03, C12, C13]
---
# P02-2l — Platform context/create/link codec'leri

**Tarih:** 2026-11-02. a üst kartının gerçek tüketiciye geçişteki ilk dar birimi; aynı branch ve tek nihai P02-2 PR'ı.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçtiği private owner/projeyi provider'ın bildirdiği verilerle karşılaştırabilir; create ve ayrı proje bağlantısının cevapları güvenli dar modellere dönüştürülür. Yerel journal gerçek provider yanıtını henüz tüketmez.

## Giren ve girmeyen kapsam

Context/create/link/detail/my-role strict projection ve body/segment güvenliği girer. Ağ çağrısı, grant/fiyat producer'ı, presign/PUT/confirm, public CLI/Python ve canlı kabul bu kart değildir.

## Bağımlılıklar ve kararlar

ADR-0024/0025/0026 Accepted; k verified sonrası kod başlar. [Platform tüketici referansı](../../reference/platform-upload-consumer.md) exact oracle'dır; observations authority değildir. Mevcut kullanıcı onayı yeni canlı yazma yetkisi doğurmaz.

## Sözleşme ve uygulama sınırı

Domain private strict projection; application raw-tree ve request codec; adapter daha sonraki HTTP diliminde bağlanır. Public caller raw proof veya verified flag veremez. Bilinmeyen metadata bütün literal/JSON sınırlarından sonra atılır.

## Kabul

Root/envelope/list, strict bool/UUID/type/size, eksik-null, owner/project/private ve known-ID/detail kontrolleri; kısa/uzun credential dinamik segment/body/atılan metadata sınırları. Create ID tek başına success değildir, link ayrı etkidir. My-role upload etiketi gerçek grant üretmez. Literal sentetik fixture'lar gerçek sözleşme sınırlarını ve ret kodunu saptar.

## Doğrulama

Contract negatifleri, Ruff, strict mypy, belge/rehber/diff; commit ve fresh R1/fix + farklı fresh R2/fix. Ağ/live/native/build yapılmaz; bütünleşik kabul c'dedir.

## Teslim kaydı

- PR/commit: [480cf04](https://github.com/HodeTech/Yorunge/commit/480cf04).
- Sonuç: Context/create/link/detail/my-role codec ve iki fresh review turu tamamlandı; local UUID hata sınıfı ile serialization öncesi private/scalar revalidation düzeltmeleri bağımsız teyit edildi. Son 122 codec testi geçti; [kabul kaydı](../../research/p02-2-implementation-validation.md#p02-2l--platform-control-codecleri).
- Kalan sınır: Pure codec kabulüdür; HTTP, producer, public CLI/Python, upload/native/build/CI/live bu kartın teslimi değildir.
