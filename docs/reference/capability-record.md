# Yetenek kaydı sözleşmesi

**Durum:** Tasarlanan v1 sözleşmesi. **Tarih:** 2026-10-27.

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

Bir kaydın `supported` olması başka hedef/yetki/hesap/araç/sürüm/ortama yayılmaz. Eski kayıt, yenilenmesi gereken kritik planda otomatik geçerli sayılmaz. Her 403 access eksikliği de değildir; yanlış key/endpoint veya sözleşme hatası ayrıca ayrıştırılır.

Bu kayıt dış uyumu anlatır. Yörünge özelliğinin planlandı/uygulandı/yayımlandı durumu [yetenek matrisindedir](../capability-matrix.md); iki durum tek enum'da birleştirilmez.
