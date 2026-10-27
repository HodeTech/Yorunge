# CapabilityScopeV2 wire sözleşmesi

**Durum:** Accepted ve uygulandı — [ADR-0013](../decisions/0013-scoped-capability-cache.md) ile 2026-10-27 kullanıcı onayı; P01-3a bütün kabul/review sürüyor. **Tarih:** 2026-10-27. Mevcut offline v1 Scope/Capability/Plan değişmez. Bu belge yeni scope'un alan, tip ve kanonik bayt biçiminin tek kaynağıdır; kayıt/TTL/güven politikasının nedeni ADR'dedir.

## Ortak türler ve kodlama

Her nesne kapalıdır: aşağıda sayılmayan alan, eksik alan veya duplicate JSON key reddedilir. Nullable alan **zorunlu olarak bulunur**, bilinmiyorsa JSON null'dır; alan atlama veya boş string null yerine geçmez. Sayılar strict integer'dır, boolean/float/string kabul edilmez. NaN/Infinity, geçersiz UTF-8 ve eşleşmemiş Unicode surrogate reddedilir.

| Tür | Kesin sınır |
|---|---|
| `Identifier` | 1–128 ASCII karakter, `^[A-Za-z0-9][A-Za-z0-9_.-]*$` |
| `Permission` | 1–128 ASCII karakter, `^[A-Za-z0-9][A-Za-z0-9_.:/-]*$`; case korunur, `*`/wildcard yoktur |
| `OpaqueText` | 1–256 Unicode code point ve en çok 1.024 UTF-8 bayt; U+0000–001F/U+007F–009F kontrol karakterleri yoktur |
| `UUIDv4` | Küçük harf, hyphen'lı kanonik UUIDv4; version/variant bitleri doğrulanır |
| `PositiveInt64` | Strict integer, 1…2^63−1 |
| `Digest` | SHA-256 için tam 64 küçük ASCII hex karakter; iddia edilen içeriğin doğrulandığı anlamına gelmez |

String'lerde trim, case-fold, NFC/NFKC veya locale dönüşümü yoktur. Semantik olarak farklı byte/code point dizileri birleştirilmez. Hedef alanlarının tek istisnai normalleştirme kaynağı [service-target-v1](credential-binding-v1.md#hizmet-hedefi-service-target-v1)'dir. Unicode sağlayıcı verisi gerekirse trusted adaptör tarafından açık, kayıpsız eşlenir; bu wire parser sessiz dönüştürmez.

Hash ve depolama için kanonik temsilde nesne anahtarları sıralanarak `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` yazılır; BOM/newline yoktur. Public Result JSON'unun biçim/key sırası bu canonical blob olmak zorunda değildir. Diziler aşağıdaki kanonik sırada olmak zorundadır; wire girdisinde sırasız/duplicate dizi reddedilir. Producer ham veriyi modele girmeden önce bu sıraya koyabilir. Bir scope'un kanonik boyutu en çok 16 KiB; bütün capability kaydı ayrıca ADR-0013'ün 32 KiB sınırına tabidir. Tekil alan sınırlarına uymak toplam boyut sınırını kaldırmaz.

## Zorunlu üst alanlar

| Alan | Tür / nullability |
|---|---|
| `schema_version` | Integer literal 2 |
| `store_id`, `identity_epoch` | `UUIDv4`, null değil |
| `clock_generation` | `PositiveInt64`, null değil |
| `service_id` | `local`, `evren-platform` veya `evren-llm`, null değil |
| `service_origin`, `api_base_path` | Her biri string veya null; uzak hizmette binding v1'in kanonik tam hedefi, birleşik uzunluk ≤2.048 karakter |
| `account_id`, `project_id` | `Identifier` veya null; mevcut context tercihi, tek başına doğrulanmış hesap iddiası değil |
| `credential_id` | `UUIDv4` veya null |
| `credential_revision` | `PositiveInt64` veya null |
| `authorization_scope` | Aşağıdaki `AuthorizationScope` nesnesi veya null |
| `model` | Aşağıdaki `ModelBinding` nesnesi veya null |
| `tool` | Aşağıdaki `ToolBinding` nesnesi veya null |
| `execution` | Aşağıdaki `ExecutionBinding` nesnesi, null değil |

Credential ID/revision birlikte dolu veya birlikte null olur. `local` için origin/API kökü, credential çifti ve authorization_scope null'dır; seçilmiş hesap/proje metadata'sı varsa ayrı alanlarında korunur, yerel yetki kanıtı sayılmaz. Uzak hizmette hedef ikilisi doludur; credential henüz bilinmiyorsa çift null olabilir ve authorization_scope da null olmak zorundadır. Authorization doluysa aynı hizmet/hedef/credential'a ait bağımsız trusted doğrulama gerekir. Bu yapısal koşullar kanıt otoritesinin yerine geçmez.

Null model/tool, o bağın kullanılmadığı veya henüz bilinmediği durumdur; görev gereksinim portu bu ayrımı belirler. Gerekli fakat bilinmeyen bağ destek/onay sağlamaz. Hiçbir null alan wildcard değildir; etkin cache eşitliği tam nesne eşitliğidir. Tarihsel aday arama etkin eşleştirme değildir; ADR-0013'te ayrı tanımlanır.

## Kapalı alt nesneler

`AuthorizationScope` tam iki alan taşır:

| Alan | Tür ve sıra |
|---|---|
| `permissions` | `Permission[]`; Unicode code point sözlük sırası (ASCII değerlerde ordinal sıra), tekrarsız |
| `resources` | `ResourceGrant[]`; `(namespace, resource_type, resource_id)` tuple'ının code point sözlük sırası, bu tuple tekrarlanamaz |

`ResourceGrant` tam `namespace: Identifier`, `resource_type: Identifier`, `resource_id: OpaqueText`, `permissions: Permission[]` taşır; izinler aynı sıralı/tekrarsız kurala uyar. `len(permissions) + len(resources) + sum(len(r.permissions) for r in resources) <= 128` olmalıdır. Aynı kaynak iki satıra bölünüp limit/tekillik aşılmaz. Boş doğrulanmış kümenin tek biçimi `{"permissions":[],"resources":[]}`; bilinmeyen izin ise null'dır. Resource sırası JSON metnine, locale'e veya hash'e göre belirlenmez.

| Nesne | Tam alan kümesi |
|---|---|
| `ModelBinding` | `source: Identifier`, `id: OpaqueText`, `revision: OpaqueText \| null`, `content_digest: Digest \| null` |
| `ToolBinding` | `id: Identifier`, `version: OpaqueText \| null`, `executable_digest: Digest \| null`, `environment_digest: Digest \| null` |
| `ExecutionBinding` | `backend: local \| evren-managed \| evren-workspace`, `runtime_id: OpaqueText \| null`, `runtime_revision: OpaqueText \| null`, `environment_digest: Digest \| null` |

Runtime ID/revision birlikte dolu veya birlikte null olur. Backend seçimi bilinir, runtime/environment doğrulaması bilinmeyebilir. Model revision ve content digest farklı bağlardır; branch/tag adı tek başına içerik doğrulaması değildir. Araç ortamı ile execution ortamı ayrı eksenlerdir; biri diğerini doldurmaz. Kaynak/tool/backend kimliklerinin şemaya uyması bir adaptörün uygulanmış/desteklenmiş olduğunu göstermez.

## Cache anahtarı

Tam anahtar girdisi kapalı `{"capability_id": Identifier, "task": Task, "scope": CapabilityScopeV2}` nesnesidir; `Task` mevcut kayıtlı görev enum'udur. SHA-256 yukarıdaki kanonik baytlardan hesaplanır. Kayıtlı tam anahtar baytları da karşılaştırılır; digest aynı fakat baytlar farklıysa kontrollü tutarsızlık hatasıdır. Producer/politika sürümü karar kabulünde ayrıca doğrulanır; profil/env adı anahtara eklenmez.

**Örnek yalnız önerilen local scope biçimidir; ürün çıktısı veya execution desteği değildir:**

```json
{
  "schema_version": 2,
  "store_id": "11111111-1111-4111-8111-111111111111",
  "identity_epoch": "22222222-2222-4222-8222-222222222222",
  "clock_generation": 1,
  "service_id": "local",
  "service_origin": null,
  "api_base_path": null,
  "account_id": null,
  "project_id": null,
  "credential_id": null,
  "credential_revision": null,
  "authorization_scope": null,
  "model": null,
  "tool": null,
  "execution": {
    "backend": "local",
    "runtime_id": null,
    "runtime_revision": null,
    "environment_digest": null
  }
}
```

Gösterim okunabilir JSON'dur; anahtar üretiminde yukarıdaki compact/sort kuralı uygulanır. Contract testleri iki bağımsız oluşturucunun aynı bayt/digest'i üretmesini; sırasız/duplicate wire reddini; Unicode composed/decomposed ayrımını; eksik/extra/null/yanlış tür/limit/local-remote negatiflerini sınar. [Uygulama ve kabul kaydı](../research/p01-3-implementation-validation.md) bu alt kümenin gerçek kanıtını taşır; wire onayı uzak hesap erişimi değildir.
