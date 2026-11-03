---
id: P02-2u
phase: P02
status: verified
size: M
depends_on: [P02-2t]
capabilities: [C03, C12, C13]
---
# P02-2u — Upload çevrimdışı bütünleşik kabulü

**Tarih:** 2026-11-03. Aynı P02-2 dalı/tek nihai development PR’ı. Üst c kabulünün dar kod/test birimidir; epik kapanışı değildir.

## Kullanıcı sonucu ve mevcut eksik

Ortak CLI/Python akışı küçük örneklerde vardır. İlk ID çıktısından önce öldürülen işi yalnız belgelenmiş CLI ile bulma ve 128 dosyanın tamamını gerçek tüketiciyle sonuca taşıma kabulü bütünleşik olarak tamamlanmalıdır. Yeni testlerin exception sınırları da Sonar’ın tek throwing invocation kuralına uygun hale getirilmelidir.

## Giren ve girmeyen kapsam

U.1 mevcut pytest exception bloklarının anlamı korunarak setup’ın ret sınırından ayrılması; u.2 gerçek CLI admission/kill/list/show ve azami dosya full workflow regresyonları. İş kuralı, tavan, retry, golden veya test beklentisi gevşetilmez. Büyük/native ölçüm araçları v kartında, kurulum/CI/live ve insan UX araştırması üst c’dedir. Sahte canlı kabul yoktur.

## Bağımlılıklar ve kararlar

T bütün kod dilimlerinde iki fresh turla verified olmalıdır. Accepted ADR-0024–0027, public/workflow/reconciliation referansları geçerlidir; yeni ürün kararı yoktur. Doküman preflight tamamlanmadan ready yapılmaz.

## Sözleşme ve uygulama sınırı

Yalnız test/fixture ve gerekli kullanıcı kabul kayıtları; ürün kusuru doğrulanırsa aynı dilimde dar düzeltme/test yapılır. Özel fault hook yalnız fixture’da kalır, public flag veya ikinci backend açılmaz. Manifest 128 normal dosyaya sahiptir; iki eşhash/farklı ad ve duplicate-safe confirm kuralı korunur.

## Kabul

Admission COMMIT’inden ilk ID teslimine kadar gerçek SIGKILL: yalnız CLI list/show --plan-id ile aynı ID, sıfır config/env/source/HTTP; yeni start pending/latch durumuna göre güvenli exit2/5, sıfır yeni permit/yazma. 128 dosya: tam 2+3N intent/accepted receipt, distinct object/item bağları ve son metadata proof; azami 128 korunur, 129 önce kontrollü ret. Global store capacity/reset/recovery rezervi mevcut regresyonlarıyla birlikte geçer. Pytest ret blokları tek throwing action taşır; hazırlık hatası beklenen ürün ret’i gibi geçemez. Her dilimde commit + iki farklı fresh review turu/fix teyidi.

## Doğrulama

-W error ile değişen contract/integration ve önceki journal/capacity/history/process kümeleri, Ruff/strict mypy/doc/skill/diff. İnsan UX, canlı hesap, native ve bütün üç ortam kabulü burada yapılmış sayılmaz.

## Teslim kaydı

- PR/commit: [U.1 test sınırları](https://github.com/HodeTech/Yorunge/commit/cfe9737), [U.2 gerçek süreç/azami envanter ve memo payı](https://github.com/HodeTech/Yorunge/commit/2eaa729); tek nihai PR aynı daldadır.
- Sonuç: İki kod diliminde ikişer farklı fresh review turu kapandı. [Kanonik kabul kaydı](../../research/p02-2-implementation-validation.md#p02-2u2--public-süreç-ve-azami-envanter) ilk retleri/fix’i, 84 testlik geniş kaynak teyidini ve bağımsız max128/386 graph, gerçek CLI kill/ID,129 ret, semantik/son kapı sonuçlarını taşır. Kart yerel verified.
- Kalan sınır: W kaynak bakımı, V kurulu/native ölçüm araçları ve üst c kurulum/son kaynak CI/kayıpsız kanıt/ayrı live/human UX sınırı açıktır. U başarısı epik veya gerçek sağlayıcı kabulü değildir.
