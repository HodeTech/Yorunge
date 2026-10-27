# ADR-0009: Development PR akışı ve Master release dalı

**Durum:** Accepted. **Tarih:** 2026-10-27. **Dayanak:** Kullanıcının dal/PR/release tercihi ve araştırma sonrası onayı.

## Bağlam

İlk uygulama `feat/offline-core` dalında yerel commit olarak hazır; uzakta yalnız korumasız `Master` ve belge temeli var. Kullanıcı geliştirmeleri PR ile ayrı bir dala almak, release'e aktarımı kendisi yapmak ve commit geçmişini korumak istiyor.

## Karar

`development`, mevcut `Master` üzerinden oluşturulur ve varsayılan geliştirme/PR dalı olur. `Master` release dalı olarak kalır; aktarım yalnız aynı deponun `development` dalından PR ile, kullanıcı tarafından yapılır. Her iki aşama merge commit kullanır; squash/rebase merge kapatılır. Koruma ve CI'nın tek kanonik tanımı [Git/yayın standardındadır](../standards/git-release.md).

İlk uygulama ve politika ilk development PR'ında birlikte alınır; var olmayan check'i zorunlu yapıp kurulumu kilitlememek için gerçek check kimlikleri aşamalı doğrulanır. Paket yayın workflow'u bu kararla eklenmez; release hazırlığı ve güvenlik kapıları hâlâ geçerlidir.

## Alternatifler ve sonuçlar

Tek `Master` üzerinden geliştirme daha basittir ancak kullanıcının release'e alma sınırını sağlamaz. Squash kısa özellik PR'larında kullanılabilir; iki kalıcı dal arasında tekrar eden aktarımda orijinal commit soyunu korumaz. GitHub rebase merge commit kimliklerini değiştirir. Merge commit daha dallı bir geçmiş üretir; `git log --first-parent` birleşmeleri taramak için yeterlidir.

Tek yazma yetkilisi varken 1 zorunlu review kişinin kendi PR'ını kilitler; bu nedenle PR + CI zorunlu, onay sayısı şimdilik 0'dır. `development` strict check, seri kullanıcı aktarımı yapılan `Master` loose check kullanır; bu tercih her salt merge commit'i geri taşıma döngüsünü önler. Aynı kimlikle çalışan ajanı kullanıcıdan GitHub izniyle ayırma garantisi verilmez.

Resmî kaynaklar (erişim 2026-10-27): [merge yöntemleri](https://docs.github.com/en/pull-requests/reference/pull-request-merges), [dal korumaları](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [PR yazarının review sınırı](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews), [workflow olayları](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows). Bunlar platform sözleşmesidir; gerçek repo ayarları ayrıca geri okunur.
