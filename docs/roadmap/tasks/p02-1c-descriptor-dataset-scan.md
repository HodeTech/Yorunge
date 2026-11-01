---
id: P02-1c
phase: P02
status: verified
size: M
depends_on: [P01-3b, P02-1b]
capabilities: [C03, C04]
---
# P02-1c — Descriptor envanteri ve güncel byte doğrulaması

**Tarih:** 2026-11-01. [Paket/adım 3](../p02-1-delivery-plan.md). Descriptor scan/verify yerelde ve iki fresh review turuyla tamamlandı; public API/CLI/yayın sonraki karttadır.

## Kullanıcı sonucu ve mevcut eksik

Veri sorumlusu klasörün tamamındaki normal dosyaların güncel ad/boyut/hash kümesini elde eder ve eski manifestle karşılaştırır. Mevcut explicit DescriptorInputs recursive envanter ve global dosya/dizin son kontrolü sağlamaz.

## Giren ve girmeyen kapsam

Tek worker, bounded descriptor recursive scan; no-follow root/ancestor/file, gerçek regular stat, güncel SHA-256, son üyelik/imza/root kontrolü ve aynı ortak çekirdekte verify/mismatch. Content-format/etiket doğrulaması, staging, upload, state/cache veya hash dedup yoktur. Dosya artifact yayını ve public CLI sonraki karttır.

## Bağımlılıklar ve kararlar

P01-3b [PR #8](https://github.com/HodeTech/Yorunge/pull/8) ve [PR #9](https://github.com/HodeTech/Yorunge/pull/9) ile verified; [execution sınırı](../../reference/execution-plan.md) korunur. P02-1b same-branch commit/test/iki review ile kabul edilmelidir. ADR-0023 Accepted zorunludur; bağımlılık ayrı PR merge’ü istemez.

## Sözleşme ve uygulama sınırı

[Manifest referansı](../../reference/dataset-manifest.md) path/byte/deadline ve mismatch semantiğini belirler. Domain kuralları ortak application akışında, gerçek descriptor/scandir/stat/read adaptördedir; CLI kural kopyalamaz. Uzun hash transaction veya state/env içinde yapılmaz. Girdi/parser ve tamamlanmış uyuşmazlık hataları ayrıdır.

## Kabul

1. Gerçek geçici dosya ağacı, boş/Unicode/hidden/nested dosyalar, aynı hash ve hardlink adları bağımsız oracle’a tam eşittir; her path ayrı hash’lenir ve byte sayılır. Başka root’ta aynı küme verify geçer.
2. Missing/extra/modified/same-size dosyada tamamlanmış tarama kapalı mismatch sayı/digest’i ve exit 7 için doğru çekirdek hatayı üretir. Yanlış manifest öncesinde dosya taranmaz; bozuk/kesilmiş scan mismatch diye sunulmaz.
3. Root/ancestor/leaf/dangling symlink, FIFO/socket/device, farklı device ve izin/okuma hatası kontrollü rettir; içerik öncesi platform/flag kapısı, no unsafe fallback ve FD kapanışı gerçek descriptor testleriyle doğrulanır.
4. Root/ancestor swap, directory ekleme/silme/rename, file replace/truncate/grow ve aynı boyutta değişim hash sırasında ve başka dosya okunurken enjekte edilir; son dosya/membership/root denetimi gözlenen değişimi reddeder. Eşzamanlı bütün değişimleri engelleyen snapshot/sandbox iddiası yoktur.
5. Dosya/dizin ayrı adet, depth/path byte, 1 GiB ve 30 s tavanları gerçek sınırlı iş/okuma ile denetlenir. Sınırda EOF aramak için bütçe dışı byte okunmaz. Kaynak `st_dev` ve hardlink sayımı politikası sınanır. Açık scanner FD ≤64 ve worker 1’dir; çok boş dizin sınırsız metadata işi üretemez.
6. Başarı/hata/KeyboardInterrupt ve enjekte edilen CancelledError bütün FD’leri kapatır; CancelledError cleanup sonrası aynen yayılır; iptal başarılı manifest veya otomatik tekrar üretmez. Env/config/state/ağ/ML guard’ları bağımsız yerel yolu doğrular.

## Doğrulama

Contract ve gerçek filesystem integration/process/race testleri, anlamlı byte/deadline sınırları, format/lint/strict mypy. Hash/memory 16/256/1.024 MiB ve yoğun metadata performansı final kurulu kabulde ayrıca ölçülür; unit test başarıları bunun yerine geçmez. Commit ve iki fresh review sonucu [kayıtta](../../research/p02-1-implementation-validation.md) tutulur.

## Teslim kaydı

- PR/commit: [5695c62](https://github.com/HodeTech/Yorunge/commit/5695c62), [b489516](https://github.com/HodeTech/Yorunge/commit/b489516), [06223b9](https://github.com/HodeTech/Yorunge/commit/06223b9); [PR #13](https://github.com/HodeTech/Yorunge/pull/13) içindeki yerel teslim; kullanıcı review/merge’ünü bekler.
- Sonuç: [Adım 3 kapanışı](../../research/p02-1-implementation-validation.md#p02-1c--descriptor-envanteri-ve-verify-çekirdeği), iki fresh tur ve iki ek hedefli teyit tamamlandı. 901 geniş komşu test + ek yerel config/env/state bağımsızlık guard’ı geçti; 77 kaynakta strict mypy ve Ruff format/lint geçti. Gerçek FD takibi, 4.096 dosya/root dahil 4.096 dizin sınırları ve cancel/close/race retleri kanıtlıdır.
- Kalan sınır: Public API/CLI, no-clobber artifact yayını, kurulu paket ve nihai performans/CI aynı pakette P02-1d kabulüyle ayrıca tamamlandı. Tarama atomik snapshot veya gelecekteki execution/upload izni değildir.
