---
id: P02-0b
phase: P02
status: verified
size: M
depends_on: [P02-0c, P02-0d]
capabilities: [C01, C02, C13]
---
# P02-0b — Hizmete bağlı salt okunur context gözlemi

**Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **Durum:** ADR-0020/0021 ve kullanıcı onaylı ADR-0022 kapsamında verified ve development’a teslim edildi. LLM/Platform kodu, adım başına iki fresh review, ayrı canlı consumer kabulleri, kaynak bağlı M5 ölçümü, temiz kurulumlar ve üç ortam source CI tamamlandı. [PR #12](https://github.com/HodeTech/Yorunge/pull/12) kullanıcı tarafından [9f30fd2](https://github.com/HodeTech/Yorunge/commit/9f30fd2bad7c3495120b127fefd588b4458d0f07) ile birleştirildi; [merge/CI kapanışı](../../research/p02-0-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. Paket yayını değildir. [Paket planı](../p02-0-delivery-plan.md) adım/review döngüsünü taşır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçili hizmet/hedef ve yerel credential snapshot’ıyla sağlayıcının bildirdiği dar gözlemi ve sunmadığı alanları açıkça görür. Platform reported ID/liste/seçili detail, LLM terms gözlemidir; doğrulanmış principal/hesap/proje bağı veya izin resolver’ı değildir. Eski profil tercihi provider kimliği sayılmaz. Özgün doğrulanmış kimlik/bağ ihtiyacı [P02-R1](p02-r1-verified-context-binding.md) sahibinde takip edilir. Bu işin verified teslimi public validation=unverified sabitini yükseltmez.

## Giren ve girmeyen kapsam

Tek hizmet için açık read-only keşif, ayrı tipli sonuç, ortak CLI/Python, credential snapshot/final nesil kapısı, bounded HTTP ve açık seçim/eksik kimlik deneyimi girer. Platform me/org/projects/seçili detail ile LLM terms/status; strict consumed/control ve tam raw yapısal/byte/seçili-literal denetimi, tüketilmeyen metadata atımı [kanonik referansa](../../reference/context-discovery.md) bağlıdır.

Login/browser JWT fallback, hesap/key/resource yaratma, şart kabulü, otomatik config seçimi, generic debug endpoint’i, remote izin cache’i, yeni DB şeması, model/kota toplu taraması, upload/inference ve ücretli export girmez. C01/C02’nin doğrulanmış kimlik/otorite kapsamı burada bitmiş sayılmaz; P01 producer draft/blocked sınırı değişmez.

## Bağımlılıklar ve kararlar

P01 ve P02-0a araştırma temeli tamamlandı. [P02-0c LLM](p02-0c-llm-context-discovery.md) ve [P02-0d Platform](p02-0d-platform-context-discovery.md) bağımsız hizmet kabulleri; aggregate kapanış ikisini gerektirir. ADR-0022 onayı Platform’un whole-raw decoder/formal auth-principal-pagination kapanış önkoşulunu dar gözlem için kaldırdı; önceki koşul geçirilmiş sayılmaz. Normal discovery’de negatif kontrol yoktur. Gerçek consumer/live ve son kaynak/review/PR/CI kabulü korunur.

## Sözleşme ve uygulama sınırı

[ContextDiscovery v1](../../reference/context-discovery.md) iki kapalı varyantı, overload/renderer, state, hata/null ve bütçeyi tanımlar. Domain/application kuralı somut HTTP adaptöründen ayrıdır; CLI/Python aynı kullanımı çağırır. Eski Context/config/Plan/Result/capability/state şemaları değişmez. LLM selected account/project null; profil tercihi scope unknown/not_applicable. Platform selected profil/override tercihidir, reported/provider ayrıdır; authentication unknown/identity unverified/null authority ve consistency not_guaranteed korunur.

## Kabul

1. Hizmete bağlı gözlenen alan/control kapalı minimum tüketici sözleşmesine uyar. Unknown auth/principal/tamlık desteklenmiş gibi sunulmaz; Platform metadata sonrası permission/verified türetilmez. LLM sunulmayan kimliği null/not_exposed, selected account/project null gösterir. Normal discovery’ye no-key/random negatif kontrol eklenmez; bunlar dar gözlem verified önkoşulu değildir.
2. CLI/Python aynı hedef/credential ID-revision/seçimi korur. Help ve offline context ağ/sır/DB açmaz. Yerel doctor ağ veya key içeriği okumaz; mevcut store varsa yalnız salt okunur tanılar, yoksa DB oluşturmaz. Discovery env’i bir kez okur; yanlış hizmet/fallback/browser token yoktur.
3. Gerçek TLS fixture’da 401/403/429, malformed/duplicate/nonfinite/2xx logical error, redirect/cookie/proxy/reflected literal ve geç/oversize yanıt kontrollü sonuç verir. Seçili credential kısa UTF-8 değerde tam eşitlik, en az 8 byte’ta alt dize; sabit protokol anahtarı muafiyetleri doğru şekildedir. Tüketilmeyen profil/ad/email/telefon/ham role yoktur; genel sır/PII sınıflandırma garantisi verilmez. Reported ID kişiye bağlanabilir.
4. Boş/tek/çok/duplicate/128–129 liste; profil veya override seçimi, parent farkı, eksik/yanlış route ID ve detail404 bağımsız fixture ile sınanır. Detail404 selection not_found/reason selected_project_not_found ve validation unverified; me/list404 veya yanlış detail ID invalid_response. Parent farkı unverified, ilk UUID otomatik seçilmez; incomplete/unknown tamlık ve snapshot not_guaranteed ayrıdır.
5. Credential revision/reset/clock-generation yarışı finalde state_changed olur. Platform en çok 4 GET (proje yoksa 3)/8 attempt/4 MiB; LLM 1 GET/2 attempt/1 MiB; hizmet başına toplam 30 s, response 1 MiB/output 256 KiB ve store 5 s/lock 1 s bütçesi. Cleanup/iptal veya bloke sistem I/O’su katı fiziksel süre garantisi diye sunulmaz.
6. Text/JSON/NDJSON, UTF-8/non-TTY/SIGINT/BrokenPipe ve eski Context/Plan/doctor uyumu korunur. İki hizmetli sentetik profilde ≤3 komutla doğru hizmet/explicit proje durumu, yanlış hedefe sıfır istek; sunulmayan alanlar açık gösterilir. Canlı gözlem süresi/yöntemi ayrı kaydedilir.
7. LLM kendi scoped consumer/live kabulünü; Platform gerçek me/org/empty ve kullanıcı seçili nonempty proje/detail kabulünü geçer. Unknown sonuç beklenen ürün sınırıdır. Key/principal semantiği bu dar teslimin engeli değildir; doğrulanmış bağ ihtiyacı P02-R1’de açık kalır. Canlı kabul fixture başarısıyla değiştirilmez.
8. Son kaynak tam test/statik/belge/ajan, wheel+sdist iki temiz kurulum, kaynak bağlı M5 startup/jobs, adım başına iki fresh review turu ve tek development PR/CI geçer. Eski kaynak referansı yeni source kabulü yerine kullanılamaz; merge/release kullanıcıdadır.

## Doğrulama

[Doğrulama matrisi](../../../CONTRIBUTING.md#doğrulama-seçimi) gerçek yerel TLS/subprocess/SQLite süreç yarışları ve eski wire uyumunu kapsar. Canlı read ayrı yetkili scope/sayaç/deadline ile, CI anahtarsız çalışır. Gerçek key/raw/ID/PII değerleri repoya alınmaz.

## Teslim kaydı

- PR/commit: [PR #12](https://github.com/HodeTech/Yorunge/pull/12), son PR head’i a374047; development merge’ü 9f30fd2.
- Sonuç: [LLM kabulü](../../research/p02-0-implementation-validation.md#bağımsız-llm-yerel-kabul-kapanışı), [Platform canlı kabulü](../../research/p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu) ve [son kaynak CI/paket kapanışı](../../research/p02-0-implementation-validation.md#pr-12-son-kaynak-ci-ve-paket-kapanışı) iki hizmetin üst teslimini karşılar. Üç tam takım, altı CI temiz kurulumu, güncel M5 startup/jobs ve native metadata kabulü geçti. ADR-0022 2026-11-01 açık kullanıcı onayıyla nihai gözlem sınırını benimsedi.
- Kalan sınır: [Development merge/CI kapanışı](../../research/p02-0-implementation-validation.md#development-merge-kapanışı) tamamdır; Master/release kullanıcıdadır. Public auth/kimlik/izin unknown/unverified/null kalır; doğrulanmış kimlik/bağ P02-R1’de draft’tır. Linux cache p95 aşımı korunmuş tanıdır; M5 başarısı Linux hedefinin geçtiği anlamına gelmez.
