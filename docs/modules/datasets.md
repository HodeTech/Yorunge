# Veri setleri modülü

**Durum:** Uygulanıyor; yerel alt küme verified, PR #13 / 50d68b1 ile development’a teslim edildi. **Kapsam:** C03/C04. **Faz:** P02/P03.

Yerel alt küme [P02-1 planıyla](../roadmap/p02-1-delivery-plan.md) tamamlandı. [ADR-0023](../decisions/0023-local-dataset-manifests.md) Accepted; inspect/verify CLI/Python ve no-clobber yayın [PR #13](https://github.com/HodeTech/Yorunge/pull/13) / [50d68b1](https://github.com/HodeTech/Yorunge/commit/50d68b1deab80d6fe14749d556efde1f103b5759) ile development’a teslim edildi. [Merge/CI ve kanıt kaydı](../research/p02-1-implementation-validation.md#development-merge-kapanışı) kanoniktir. İlk dilim normal dosya ad/byte envanteridir; Private create/normal dosya upload ve salt okuma uzlaştırması bu çalışma dalında uygulanmıştır; [kullanım](../reference/upload-workflows.md) ve [nihai kabul durumu](../roadmap/current.md) ayrıdır. ZIP/indirme/sürüm ve içerik-formatı hedefleri planlandı kalır.

## Planlanan uzak veri iş akışları

Yerel dosya denetimi, manifest, private veri seti oluşturma, dosya/ZIP aktarımı, indirme, resume/reconcile ve sürüm/bölme bilgisi bu modüldedir. Etiketleme editörü kurmaz; mevcut veri/etiket yapısını kontrol eder ve uygun import yolunu seçer.

Presign → PUT → confirm ile etiketli ZIP import ayrı sözleşmelerdir. Dosyanın güncel hash'i ve kök sınırı gönderim öncesi doğrulanır. Büyük içerik stream edilir; worker/byte kuyruğu sınırlıdır. Sunucu hash dedup yapıyorsa farklı yerel dosya kimliklerinin tek uzak öğeye bağlanması raporlanır; isim ve kayıt sayısı sessizce kaybolmaz.

Manifest/günlük tek gerçek kaynak değildir. Uzak öğe silinmiş, yerel dosya değişmiş veya confirm bozulmuşsa resume bunu açıklar. Bu daldaki upload yerel hash/gönderilen byte ile uzak metadata sonucunu ayırır; uzaktan byte indirme/doğrulama ve etkili resume P02-3’tedir; bugünkü datasets verify yalnız yerel Manifest v1 ile yeniden hash’lenen dosya kümesini karşılaştırır. Sürüm oluşturma/freeze gibi ek yan etkiler planın içinde görünür olmalıdır.

**Kabul:** Aynı boyutta değişim, symlink, bozuk manifest, çift dosya/hash, kesik PUT, yanlış confirm, stale journal, sayfalama ve indirme no-clobber senaryoları geçer. Kullanıcı veri seti kimliği ve eksik/kalan iş raporu alır. [Aktarım yolu](../user-journeys.md).
