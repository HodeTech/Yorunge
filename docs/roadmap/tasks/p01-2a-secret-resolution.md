---
id: P01-2a
phase: P01
status: verified
size: M
depends_on: [P01-1]
capabilities: [C01]
---
# P01-2a — Hizmete bağlı env secret çözümleme

**Hazırlandı:** 2026-10-27. Uygulama ve iki yeni bağımsız review turu tamamlandı. [Güncel kabul kaydı](../../research/p01-2-implementation-validation.md).

[P01-2 tek PR paketinin](../p01-2-delivery-plan.md) ilk uygulama adımıdır. B02/B13 kararları Accepted'dır; bu kart sıradaki uygulamadır. Bağımsız hazır olma durumu bütün paketin hazır veya uygulanmış olduğu anlamına gelmez.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir sonraki hizmet işleminde yalnız doğru servisin credential'ının kullanılmasını ister; yerel context/plan okumak için anahtar gerekmemelidir. Kart açıldığında profil env adını doğruluyor fakat secret çözümlemiyordu; bu eksik kapatıldı.

## Giren ve girmeyen kapsam

Giren: `evren-platform` / `evren-llm` hizmetine bağlı tipli env referansı, yalnız açık çözümleme çağrısında değer okuyan adaptör ve dışarı sızmayan credential taşıyıcısı. Mevcut TOML `platform_key_env` / `llm_key_env` alanları kullanılır; sır dosyaya yazılmaz. CLI/Python yerel context ve offline draft davranışı korunur.

Girmeyen: HTTP/auth denemesi, doctor/proje keşfi, keychain, DB, credential kimliği/nesli, cache, eğitim aracı veya yürütüm. Plan alanları hâlâ uzak yetki doğrulanmadığını gösterir. Bir sırrın env'de bulunması hesabın destek/yetki kanıtı değildir. Yeni “anahtarı yazdır” CLI komutu eklenmez.

## Bağımlılıklar ve kararlar

`P01-1` [PR #1](https://github.com/HodeTech/Yorunge/pull/1) ve [ilk dilim kanıtıyla](../../research/p01-core-validation.md) doğrulandı. Bu dar env çözümleme dilimi için açık dış erişim veya ek mimari karar gerekmez; kalıcı credential kimliği B02/B13 ve P01-4a/P01-2b'ye bağlı ayrı iştir.

## Sözleşme ve uygulama sınırı

Mevcut domain hata/model, application kullanım senaryosu ve dosya/profil adaptörü incelenir; env I/O domain'e konmaz. Sırrı tüketmek isteyen kullanım senaryosu hizmeti açıkça seçer; ihtiyaç duymayan mevcut API çağrıları çözümleme yapmaz. Yeni iç port/model adları uygulamada seçilebilir; henüz olmayan port varmış gibi import örneği yazılmaz.

[Config](../../reference/configuration.md) ve [CLI hata sözleşmesi](../../reference/cli-contract.md) aynı değişiklikte uygulanmış alt kümeyi günceller. Mevcut kullanıcı şeması bozulmadan yapı kurulabilir; bir alan/sürüm değişimi gerekirse açık fark/migration kaydedilir. Global credential registry kararı bu pakete çekilmez; P01-4a/P01-2b ve B13'te ele alınır.

## Kabul

1. İki hizmetin farklı env referansı ve değeri sentetik fixture'da ayrılır. Platform isteği LLM anahtarını kullanmaz; birinin yokluğu diğerine fallback üretmez.
2. Değer yalnız açık çözümleme çağrısında ve yalnız seçilen ad için okunur; rastgele env taraması veya davranış override'ı yoktur. Referansın tür/ad hatası kontrollü kullanım/config hatasıdır.
3. Seçilmiş referansın eksik/boş değeri kararlı tipli credential hatasıdır. Kimlik eksikliği exit sınıfı 3 ile eşlenir; stderr zarfı sır veya ham parser girdi taşımaz. Bu eşleme, yerel context'i credential gerektirir hale getirmez.
4. Bilinen sentetik secret; repr/str, JSON/plan/digest, hata ve log sınırlarında görünmez. İç taşıyıcının genel amaçlı serialization'ı ham değeri vermez; secret yalnız ihtiyaç duyan adaptöre kontrollü aktarılır.
5. Yardım, sürüm, context, capability ve offline plan testleri credential okumasını yasaklayan guard altında geçer. Ağ, DB, keychain, araç/model keşfi veya ML import eklenmez.
6. Mevcut seçim önceliği, açık proje eksikliği davranışı ve kayıtlı plan seçimi korunur. Credential varlığı `remote_verified=true`, `supported` veya `executable=true` üretmez.

## Doğrulama

Gerçek env adaptörü, sentetik değer ve gerçek şema kullanılır; parser veya bütün application mock edilerek doğruluk iddiası kurulmaz. Hizmet karışması, eksik/boş/yanlış referans ve çıktı sızıntısı negatif testleri; mevcut CLI/API sözleşme suite'i ve strict format/lint/type gerekir. Import veya başlangıç yolu değişirse standart benchmark, paket yerleşimi/metadata etkilenirse build/temiz kurulum eklenir. Komut kaynağı [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi).

## Teslim kaydı

- PR/commit: [İlk uygulama](https://github.com/HodeTech/Yorunge/commit/41c7dba), [review 1 düzeltmesi](https://github.com/HodeTech/Yorunge/commit/b319001); [PR #6](https://github.com/HodeTech/Yorunge/pull/6) kullanıcı review'sine açık.
- Sonuç: 466 test, Ruff format/lint, strict mypy, belge/ajan denetimleri; wheel/sdist iki temiz kurulum ve başlangıç bütçeleri geçti. Üçer yeni ajanla iki bağımsız tur tamamlandı; ilk turdaki üç P2 regresyonla giderildi, ikinci turda açık bulgu kalmadı. [Ayrıntılı kanıt](../../research/p01-2-implementation-validation.md).
- Kalan sınır: Bu alt kartta açık doğrulanmış bulgu/kabul işi yok. Kalıcı kimlik/state, init/doctor, HTTP/auth ve uzak execution P01-2a'nın teslimi değildir; sonraki adımlar kendi kanıtıyla kapanır.
