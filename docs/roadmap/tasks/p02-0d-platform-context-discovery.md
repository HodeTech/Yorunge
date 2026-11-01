---
id: P02-0d
phase: P02
status: in_progress
size: M
depends_on: [P02-0a, P01-2b, P01-3a, P01-5a, P01-5b]
capabilities: [C01, C02, C13]
---
# P02-0d — Platform salt okunur context gözlemi

**Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **Durum:** ADR-0022 kullanıcı onayıyla nihai dar gözlem sözleşmesi kabul edildi. Çekirdek/public yüzey ikişer fresh review ve önceki yerel kaynak kabulünü geçti; gerçek üç uç ve ayrı seçili-proje consumer kabulü tamamlandı. Onay sonrası son kaynak/test/kurulum/M5/review ve tek development PR/CI kabulü sürüyor; verified değildir. P02-0b’nin Platform koludur; LLM bağımsızdır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçtiği Platform hedefi/yerel credential snapshot’ıyla bildirilen ID’leri, organizasyon/proje listelerini ve profil veya açık override’daki proje detayının gözlem durumunu görür. Reported ID principal/account/üyelik veya yazma izni değildir. Auth unknown, provider identity unverified/null, authorization_scope null, validation unverified ve consistency not_guaranteed kalır. Özgün doğrulanmış hizmet kimliği/bağ ihtiyacı [P02-R1](p02-r1-verified-context-binding.md) sahibinde açık takiptedir.

## Giren ve girmeyen kapsam

GET auth/me/organizations/projects/seçili projects/{id}; strict tüketilen alan/control, bütün raw yapısal/byte ve seçili credential literal denetimi sonrası tüketilmeyen metadata atımı; kapalı PlatformContextDiscovery v1 ve ortak CLI/Python girer. Listeler en çok 128 kayıttır; unknown/incomplete tamlık ve endpoint gözlem aralığı açık gösterilir. Profil-only veya override projesi detail GET’ini tetikler; otomatik ilk öğe seçimi/config yazımı yoktur.

Browser JWT fallback, key/resource oluşturma, şart kabulü, model/kota/dataset taraması, upload/inference, permission uydurma, yeni state/cache veya yeni alt PR girmez. Ayrı whole-raw unknown-ret decoder ve formal auth/principal/pagination bilgisi bu dar gözlem tesliminin önkoşulu değildir; sonraki yan etkili tüketicinin güncel otorite/endpoint kapısı korunur.

## Bağımlılıklar ve kararlar

P01/P02-0a bağımlılıkları verified. [ADR-0020](../../decisions/0020-service-bound-context-discovery.md) hizmet/state/credential sınırını, [ADR-0021](../../decisions/0021-platform-discovery-observations.md) wire ve ilk projeksiyon başlangıcını tanımlar. [ADR-0022](../../decisions/0022-observed-platform-consumer-contract.md) 2026-11-01 açık kullanıcı onayıyla yalnız nihai Platform tüketici/kabul hükmünü değiştirir. Eski katı decoder/key-semantik koşulları kaldırıldı; geçirilmiş test sayılmaz. Gerçek consumer canlı kabulü, son kaynak/review/kurulum/ölçüm ve PR/CI korunur.

## Sözleşme ve uygulama sınırı

[Platform v1 referansı](../../reference/context-discovery.md#platform-gözlem-varyantı) tek kanonik wire/raw tüketici sözleşmesidir. Domain/application kuralı, somut HTTP adaptörü ve ortak CLI/Python kullanımı ayrıdır. LLM DTO’su ve eski Context/config/Plan/Result/state şema 6 değişmez. Detail404 → validation=unverified, selection.state=not_found ve reason selected_project_not_found; me/list404 ve yanlış detail ID → invalid_response. Parent farkı normal unverified gözlemdir; membership veya account mismatch uydurulmaz.

İstekler DB transaction dışında tek credential/config snapshot’ıyla yürür; final store/epoch/clock-generation/credential ID/revision/deadline tekrar karşılaştırılır. Tüketilmeyen profil/ad/email/telefon/ham role/admin_permissions yayımlanmaz. Reported ID kişiye bağlanabilir. Literal tarama yalnız seçili credential için kısa UTF-8 değerde tam eşitlik, en az 8 byte’ta alt dize; sabit protokol anahtarı muafiyetleri seçilmiş şekille sınırlıdır. Genel sır/PII sınıflandırma iddiası yoktur.

## Kabul

1. Tüketilen raw alan/control eksik/yanlış tür/duplicate/unknown şekil/limit/logical-success hatasında invalid_response. Bütün raw strict UTF-8/JSON/depth/node/header/byte denetimi ve seçili literal taraması korunur; tüketilmeyen metadata atılır. Public DTO extra=forbid/strict/frozen. Ayrı whole-raw unknown-ret decoder gerekmez.
2. Normal discovery’ye no-key veya random invalid-key çağrısı eklenmez; auth unknown kalır. Key 200/no-key 401 veya malformed reddi doğrulanmış key/principal değildir. İyi biçimli endpoint-bound negatif kontrol yalnız ayrıca yetkili, grameri kapanmış opsiyonel araştırmadır (önceki contract pilotu ≤8 GET/12 attempt/4 MiB/30 s); bu kartın verified önkoşulu değildir.
3. No-init açık/default state, tek env snapshot, final credential/epoch/clock-generation yarışları; gerçek TLS/redirect/reflection/deadline/cleanup ve CLI/API eşliği sınanır. Normal en çok 4 GET, proje yoksa 3; en çok 8 attempt/4 MiB/30 s, response 1 MiB/output 256 KiB; store 5 s/lock 1 s cooperative bütçeleri korunur.
4. Boş/tek/çok/duplicate/128–129 liste, eksik/yanlış ID, total/bool/null/success, profil veya override seçimi, parent farkı/detail404/route-ID ve ASCII-sıralı reason fixture’ları bağımsız oracle ile sınanır. İlk UUID seçilmez; liste tamlığı unknown/incomplete ve uzak snapshot not_guaranteed kalır.
5. Gerçek me/org/empty ve kullanıcı seçili nonempty proje/detail consumer kabulü; son kaynak test/statik/belge/ajan, iki temiz wheel/sdist kurulumu ve kaynak bağlı M5 startup/jobs; adım başına commit+iki farklı fresh review ve tek development PR/CI tamamlanır. Canlı veri veya kaynak eksikliği yeşil fixture ile kapatılmaz.

## Doğrulama

[Doğrulama matrisi](../../../CONTRIBUTING.md#doğrulama-seçimi); sentetik anlamlı test, gerçek yerel TLS/subprocess ve iki süreçli SQLite yarışları. Canlı hesap koşuları ayrı kullanıcı yetkisi ve sayaç/deadline ile yapılır; CI anahtarsızdır. Key/raw/gerçek ID/PII değerleri repoya girmez. Son kaynak değişirse referans yeniden üretilir.

## Teslim kaydı

[Çekirdek/public yüzey ve önceki yerel kabul](../../research/p02-0-implementation-validation.md#platform-ara-yerel-kabul-kapanışı), [ilk gerçek tüketici gözlemi](../../research/p02-platform-reverse-engineering.md) ve [ayrı seçili-proje kabulü](../../research/p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu) kayıtlıdır. Seçili-proje koşusu 4 ürün GET/200 ve yeni detail no-key 401; ayrı toplam 5 GET/5 attempt/2.090 byte/0,488645 s. Önceki boş-liste/başarısız/sınır dışı araştırmalar tarihsel korunur. ADR-0022 onayıyla dış sözleşme engeli kaldırıldı; kalan son kaynak/review/PR/CI kabulü sürüyor. Kullanıcı review/merge ve Master/release ayrı süreçtir.
