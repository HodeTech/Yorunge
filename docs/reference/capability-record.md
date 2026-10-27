# Yetenek kaydı sözleşmesi

**Durum:** v1 genel sözleşme; sınırlı offline görünüm uygulandı, canlı/cache kaydı planlandı. **Tarih:** 2026-10-27.

P01-3 için ayrı v2/cache ayrıntısı [Proposed ADR-0013](../decisions/0013-scoped-capability-cache.md) ile kullanıcı onayına sunulmuştur. Bu öneri aşağıdaki uygulanmış v1'i veya henüz benimsenmemiş tasarımı değiştirmez; [hazırlık incelemesi](../research/p01-3-readiness-review.md).

## Uygulanan offline görünüm

`yorunge capabilities` / `yorunge.api.inspect_capabilities` seçilmiş context/task/tool/execution kapsamını döndürür. `planning.offline=supported` yalnız uygulanmış yerel şema/seçim politikasını anlatır; dış araç/EVREN desteği değildir. Eksik adaptör veya uyumsuz birleşim `unsupported`, doğrulanmamış hizmet/yetki/runtime `unknown`, açıkça eksik proje önkoşulu `requires_access` olur. `evren-workspace` genel kullanıcı sözleşmesi bilinmediği için erişim var/yok hükmü verilmez.

Kanıt `local_policy` veya `not_verified`; `checked_at`/`expires_at`, credential kimliği/nesli, yetki kapsamı ve araç sürümü null'dır. Bu bilinmeyen alanlar runtime/canlı kanıt gibi doldurulmaz. Aşağıdaki genel alanlardan `constraints` ve `provider_request_id` bu dar modelde henüz yoktur; bilinmeyen alanlar reddedilir. Cache ve tazelik politikası bu dilimde uygulanmadı. Plan yalnız bu kayıtları ve engelleri sabitler; yürütülemez.

| Alan | Anlam |
|---|---|
| `schema_version` | Kaydın biçim sürümü |
| `capability_id`, `task` | İncelenen işlem ve görev |
| `scope` | `service_id`, `service_origin`, `api_base_path`, `account_id`/`project_id`, `credential_id`/`credential_revision`, `authorization_scope`, model, tool/sürüm ve execution |
| `support` | `supported`, `unsupported`, `unknown`, `requires_access` |
| `reason_code`, `message` | Kararlı kod ve insan açıklaması |
| `constraints` | Model/format/parametre/boyut/süre gibi doğrulanmış sınırlar |
| `evidence` | Şema/kılavuz/istemci/sentetik test/canlı hesap kanıtı ve kaynak |
| `checked_at`, `expires_at` | UTC son doğrulama ve tazelik sınırı |
| `provider_request_id` | Varsa sınırlı tanılama kimliği; sır değildir |

`supported`: bu kapsamda yeterli kanıtla destek var. `unsupported`: bu kapsamda açık uyumsuzluk kanıtı var. `unknown`: yeterli/tutarlı kanıt yok. `requires_access`: işlem veya özellik biliniyor ama bu bağlamın yetkisi/erişim koşulu sağlanmadı.

Hizmet ve yetki bağlarının anlamı [planın içerdiği bağlarla](../architecture/execution-model.md#planın-içerdiği-bağlar) aynıdır; kayıtta sır veya anahtarın ham hash'i tutulmaz. Cache anahtarı `capability_id`, `task` ve `scope` alanlarının tamamını kapsar. Aynı hesap/projede iki ayrı anahtarın `supported` sonucu paylaşılmaz; aynı env/keychain referansında anahtar değişirse yetki kimliği/nesli yenilenir. İzin kapsamı değişince eski kayıt kullanılmaz. Yetki kimliği veya kapsamı bilinmiyorsa hesap özelinde `supported` sonucu yeniden kullanılamaz; gerekli doğrulama yapılana kadar `unknown` veya erişim eksikliği kanıtlıysa `requires_access` kullanılır. Genel şema/kılavuz kanıtı hesap yetkisi doğrulaması sayılmaz.

Registry hedef karşılaştırması ve kalıcı kimlik/nesil için [credential binding v1](credential-binding-v1.md) P01-2 ile uygulandı; [PR #6](https://github.com/HodeTech/Yorunge/pull/6) development’a alındı. Mevcut v1 offline capability kaydı değişmedi; cache/plan entegrasyonu P01-3 kapsamıdır. İki sürecin farklı credential snapshot'ı cache thrash'ine yol açabilir; revision'ı anahtardan çıkarmak çözüm değildir. P01-3, etkin nesil başına sınırlı cache/saklama ve otomatik tekrar döngüsü yerine kontrollü bağ çatışmasını gerçek kabulde doğrular.

Bir kaydın `supported` olması başka hedef/yetki/hesap/araç/sürüm/ortama yayılmaz. Eski kayıt, yenilenmesi gereken kritik planda otomatik geçerli sayılmaz. Her 403 access eksikliği de değildir; yanlış key/endpoint veya sözleşme hatası ayrıca ayrıştırılır.

Bu kayıt dış uyumu anlatır. Yörünge özelliğinin planlandı/uygulandı/yayımlandı durumu [yetenek matrisindedir](../capability-matrix.md); iki durum tek enum'da birleştirilmez.
