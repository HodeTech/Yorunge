---
id: P01-6b
phase: P01
status: verified
size: M
depends_on: [P01-2c, P01-3b, P01-4c, P01-5b]
capabilities: [C01, C02, C12, C13]
---
# P01-6b — Faz kabulü ve doğrulanmış ortam matrisi

**Tarih:** 2026-10-30. **Paket:** [Kalan P01](../p01-remaining-delivery-plan.md), adım 5–6. P01-6b kabulü tamamlandı ve PR #11 ile development’a bc9532c merge’ünde teslim edildi. [Merge/kanıt kapanışı](../../research/p01-remaining-implementation-validation.md#development-merge-kapanışı) günceldir; önceki adım/CI/performans kayıtları kaynaklarıyla korunur. Eski P01-6a CI altyapısı bu kapanış kabulü değildir.

**PR #11 inceleme takibi:** RSS baseline/büyüme, kısa secret, ADR-0019 startup kabul ortamı ve Sonar bakımı tamamlandı; kart `verified` ve development’a teslim edildi. [son kaynak kabulü](../../research/p01-remaining-implementation-validation.md#ilk-runtime-release-ci-kapanışı) gerçek üç ortam/altı kurulum ve güncel M5/Linux raw sonuçlarını taşır. PR #11 merge ve son belge/merge artifact saklama takibi [kapanış kaydındadır](../../research/p01-remaining-implementation-validation.md#development-merge-kapanışı).

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı/sonraki adaptör geliştirmesi, kurulu hafif çekirdeğin girdi→kimlik→plan/onay→operation→tipli sonuç→restart akışını ve hatada ne kaldığını [kanıtlı kapanış kaydından](../../research/p01-remaining-implementation-validation.md#ilk-runtime-release-ci-kapanışı) izleyebilir. Bu kartın uygulama/kabul işi tamamlandı; canlı EVREN/ForgeLM adaptörü ve yayın kapsam dışıdır.

## Giren ve girmeyen kapsam

Ürün çekirdeği ile gerçek TLS loopback/süreç/SQLite uçtan uca sentetik kabul, source-matched performans, wheel/sdist iki kurulum, CI uyumluluk matrisi ve durum/belge kapanışı girer. Gerçek EVREN/ForgeLM adaptörü, ücretli çağrı/GPU, veri seti upload/uzak artefakt teslimi, Windows state desteği, fiziksel güç kesintisi, Master/release/yayın kapısı bu kartta yoktur. Bunların sınırını kaydetmek açık P01 kabulünü ertelemek değildir.

## Bağımlılıklar ve kararlar

P01-2c/3b/4c development'a teslim edildi. P01-5b aynı dalda 0bf70a4 runtime/2515533 süreç fixture’ı, iki fresh review ve iki kurulumla verified; bu kartın doğrudan bağımlılıkları kapanmıştır. ADR-0017/0018 Accepted; ilgili uygulama kabulü önkoşuldur. Kullanıcının kalan işler talebi tek nihai PR için yetkidir; ayrıca belge PR'ı veya test merge'ü açılmaz.

## Sözleşme ve uygulama sınırı

Genel test/kurulum komutlarının tek kaynağı [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi), bütçe/yöntem [performans standardı](../../standards/performance.md), ölçüm saklama [kanıt standardı](../../standards/research-evidence.md)'dır. Bütünleşik fixture gerçek ürün port/renderer/kurulu paket kullanır; fake provider yalnız test katmanında kalır. Durum değişimi yalnız gerçek kanıta dayanır.

## Kabul

1. Yeni config/state→seçilmiş credential kimliği→fixture account/proof capability→immutable plan/input validation/digest approval→kalıcı operation/attempt→gerçek TLS taşıma/çok-olay stream→tipli terminal sonuç; ayrı süreç/restart sonrası CLI/Python jobs aynı kayıt/ID/digest/outcome'u okur. Beklentiler uygulama çıktısından türetilmiş oracle değildir.
2. Wrong-target/auth/revoke/credential yarışları ve yan etki sonrası kayıp response/SIGKILL/cancel/deadline negatifleri: eski sahip yazamaz, en çok 1 fixture effect, latch korunur, unknown yalnız trusted aynı-job gözlemle çözülür. Kesik stream, izlemeyi bırakma ve doğrulanmış provider cancellation ayrıdır. Prearm ret sıfır request/effect'tir.
3. Wheel ve sdist ayrı frozen runtime ortamlarında depo dışından import/konsol/metadata ve yeni transport/stream smoke'unu geçer. Paket üye izin listeleri, özel girdi ve raw arşiv dışlama, mevcut v1/cache/execution/jobs smoke ve lazy network/secret/ML guard korunur.
4. Son runtime kaynağında tam test/Ruff/mypy/docs/agent/evidence/diff kapıları; kurulum/CI test sonucu source SHA, OS/arch/Python/SQLite ve paket sürümüyle kaydedilir. Linux 3.11/3.14 ve macOS 3.11 uyumluluk işi CI'da çalıştırılır; gerekli offline-core adı korunur ve başarısız/iptal/atlanan alt iş aggregate'i yeşile çeviremez. Bunlar gerçekleşmeden ortam verified yapılmaz. Gerçek SQLite 3.37 veya Windows koşusu yoksa açık not kalır; minimum hedef gerçek koşuyla karıştırılmaz.
5. Mevcut 500/200 ms paired startup ve normal/yoğun 30-process jobs kapıları son kaynakla tekrar doğrulanır; yeni HTTP import'u yerel yola girmez. Jobs için önceki aynı host/disk şartının [somut referansı](../../standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) korunur; başarılı kaydın bütün kaynak/lock/fixture/ölçüm kodu baytları CI'da güncel checkout ile zorunlu eşleştirilir. Başka ortamın jobs aşımı başarıya çevrilmez veya CI genel yeşiliyle performans geçti sayılmaz. State 5 s/coordinator 30 s kontrol deadline'ları ve yoğun fixture davranışı korunur; ilgili hot-path değiştiyse operation/migration bütçe probe'ları son kaynakla koşulur, eski kayda güvenilmez. Aşım skip veya tolerans artırımıyla gizlenmez.
6. Gerçek raw stream 16/256/1.024 MiB sentetik byte'ı bütününü biriktirmeden hash/sayıyla tüketir; ölçülen üç boyutun RSS aralıkları en çok 8 MiB çapraz boyut farkını kanıtlar; bu sonlu boyut kabulü asimptotik ispat değildir. Her boyutta istemci ek RSS üst sınırı≤64 MiB, en çok 2 bağlantı/32 KiB parça, bounded backpressure ve request sayısı kayıtlıdır. Server ayrı süreç ve RSS ölçümünden hariç; TLS/istemci baseline ve örnekleme yöntemi açıklanır. Uygulanan byte taşıma kabulü dataset endpoint desteği değildir.
7. Kapanış raporu her kart/step/review/fix ve olumlu/negatif/performans kanıtını eşler; başarısız ara koşular saklanır. Raw arşiv/hash/özet tooling gerekirse kapalı yeni report türüyle genişletilir ve gerçek negatif testlerle denetlenir. current/faz/matris/referans/modül/README/changelog tutarlı; yalnız tamamlanan P01 alt kapsamı verified olur. PR son head CI/review kullanıcıya sunulur; merge/release yapılmaz.

## Doğrulama

Fixture-only gerçek loopback/TLS/process/state, bağımsız contract oracle, artifact install ve ölçüm helper'ları; bütünleşik son test/CI. Ortam hücreleri pass/fail/not_run olarak ayrılır; doküman veya pipeline tanımının varlığı acceptance sayılmaz. Her adım commit+iki farklı fresh review turu içerir.

## Teslim kaydı

**Development teslimi:** [PR #11](https://github.com/HodeTech/Yorunge/pull/11), [merge bc9532c](https://github.com/HodeTech/Yorunge/commit/bc9532cd66c76dc4126162fabd4307c2fdaf4027), 2026-10-30 07:57:27 Europe/Istanbul; [merge/kayıt kapanışı](../../research/p01-remaining-implementation-validation.md#development-merge-kapanışı).

- PR/commit: [PR #11](https://github.com/HodeTech/Yorunge/pull/11), son kaynak e5846ce, gerçek CI head de312dc; [CI 40975685731](https://github.com/HodeTech/Yorunge/actions/runs/40975685731). İlk-release A/A, normal pinned runtime ve özgün witness saklama doğrulandı.
- Sonuç: [ADR-0019/Sonar kaynak kabulü](../../research/p01-remaining-implementation-validation.md#ilk-runtime-release-ci-kapanışı), iki güncel M5 referansı, gerçek Linux raw v2, üç ortam tam takımı ve altı kurulum verified. Üç bilinçli S5754 dışında kullanıcı Sonar maddeleri açık listeden çıktı.
- Kalan sınır: M5 kabulü Linux performansı veya donanım attestasyonu değildir; önceki retler korunur. Son PR/iptal/merge koşusu çıktıları bu kapanışta ADR-0019’a göre kalıcı arşive alındı; 149 kayıt ve gerçek merge CI doğrulandı. Development teslimi tamamlandı; Master/release kullanıcıdadır.
