---
id: P01-2b
phase: P01
status: draft
size: M
depends_on: [P01-2a, P01-4a]
capabilities: [C01, C13]
---
# P01-2b — Credential kimliği, nesli ve hedef bağları

**Tarih:** 2026-10-27. **Teslim paketi:** [P01-2](../p01-2-delivery-plan.md). B13 kararı ve doğrudan bağımlılıklar beklenir.

## Kullanıcı sonucu ve mevcut eksik

Aynı profil/env adı altında credential veya hedef değişince eski bağ kullanılmamalıdır. Bugün kimlik/nesil alanları null'dır ve env değeri hiç okunmaz.

## Giren ve girmeyen kapsam

Hizmet/hedef/referans ayrımı, rastgele opak kimlik, gözlenen değişimde ilerleyen nesil ve süreçler arası kayıt girer. Ham credential veya ham hash DB/çıktıya yazılmaz. Capability cache, execution onayı ve gerçek auth/izin doğrulaması sonraki işlerdir; env'de değer bulunması uzak erişim desteği değildir.

## Bağımlılıklar ve kararlar

P01-2a ve P01-4a aynı dalda kanıtlı tamamlanır. [ADR-0012](../../decisions/0012-credential-identity-and-change-detection.md) Proposed kararı kullanıcı tarafından kabul edilmelidir; yerel karşılaştırma anahtarı/koruma/kurtarma seçimi onaydan önce uygulanmaz.

## Sözleşme ve uygulama sınırı

[Plan bağları](../../architecture/execution-model.md#planın-içerdiği-bağlar) ve [capability kapsamı](../../reference/capability-record.md) kanoniktir. Sır bir kez çözülür; taşıyıcı/hedef/kimlik aynı gözlemi temsil eder. Public config/plan biçimi değişirse açık uyumluluk farkı ve gerçek CLI/Python testiyle birlikte belgelenir; offline draft uzak yürütme planına yükseltilmez.

## Kabul

1. Hizmet/origin/API kökü/referans ve hesap/proje bağları karışmaz; profil adı tek başına kimlik değildir.
2. Aynı gözlem süreç yeniden açıldığında aynı kimlik/nesli kullanır; gözlenen A→B→A değişimi eski nesli geri getirmez. Birbirinden bağımsız env snapshot'ları için tutarlılık sınırı belgelenir.
3. Eşzamanlı aynı/değişik değer gözlemleri işlemseldir; kayıp artış veya aynı kimlik/nesil altında iki farklı gözlem oluşmaz.
4. Onaylı mekanizmanın özel karşılaştırma kaydı public serialization/digest/log/hata içine girmez; raw secret ve raw hash saklanmaz. Sentetik sızıntı testleri bütün sınırları kapsar.
5. Yerel koruma verisi kayıp/bozuk/uyumsuzsa otomatik yeniden üretimle eski bağ kabul edilmez. Onaylı kurtarma yolu yeni kimlik alanı üretir, eski bağları reddeder ve operation geçmişini silme sözleşmesi oluşturmaz.
6. Plan seçimi, salt yerel komutların sır okumaması ve `remote_verified=false`/yürütülemez offline davranış korunur.
7. [Ortak binding sözleşmesinin](../../reference/credential-binding-v1.md) hedef örnekleri, tam JSON/message/tag byte vektörleri, env/secret uzunlukları, revision taşması ve değişmeden eski v1 Plan yükleme kabulü doğrulanır.
8. Canlı DB reset'i ile identity-only DB restore ayrıdır. Reset geçmişi silmez; restore'un kayıt kaybı açıkça gösterilir. Restore kilidi/kalıcı intent, kesinti ve yeni epoch/key doğrulaması eski bağı yeniden aktifleştirmez. Operation tüketicisi sürümünde restore ret kapısı P01-4b kabulüdür; bu karta tamamlanmış operation koruması yazılmaz.

## Doğrulama

Gerçek env adaptörü, geçici gerçek DB/yerel koruma ve ayrı süreçler; hizmet karışması, rotation, eksik/bozuk veri, concurrency ve sızıntı testleri. HMAC seçilirse standart test vektörü ve constant-time karşılaştırma kullanımı incelenir; özel kripto tasarlanmaz. Test/build/ölçüm seçimi [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) içindedir.

## Teslim kaydı

Ürün uygulaması ve bu karta ait teslim kanıtı henüz yoktur. Yerel araştırma probe'u kabul testi veya tamamlanmış credential adaptörü sayılmaz.
