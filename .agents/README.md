# Yörünge ajan çalışma rehberi

**Güncellendi:** 2026-10-27. Kanonik kurallar [AGENTS.md](../AGENTS.md), iş sırası [current](../docs/roadmap/current.md), kamu sözleşmeleri [reference](../docs/reference/README.md) altındadır. Skill kuralları çoğaltmaz; doğru kaynağı doğru görevde kullanmayı sağlar.

## Giriş ve görev seçimi

| Kullanıcı talebi | Skill | Beklenen sonuç |
|---|---|---|
| “Bu faz maddesini daralt, ne yapacağımızı planla” | [yorunge-plan-task](skills/yorunge-plan-task/SKILL.md) | Kapsam/bağımlılık/kabulü net kart; yalnız plan istenmişse kod yok |
| “Hazır P01-2a işini uygula” | [yorunge-implement-task](skills/yorunge-implement-task/SKILL.md) | Çalışan dar sonuç + anlamlı test + belge |
| “Config/CLI/API veya sağlayıcı sözleşmesini değiştir” | [yorunge-contract-change](skills/yorunge-contract-change/SKILL.md) | Şema-tüketici-hata-belge uyumu |
| “Kontrolleri çalıştır, paketi/ölçümü doğrula” | [yorunge-verify](skills/yorunge-verify/SKILL.md) | Gerçek geçen/kalan/koşulmayan kontrol kaydı |
| “PR'ı, kodu veya belgeleri review et” | [yorunge-review](skills/yorunge-review/SKILL.md) | Önem sıralı kanıtlı bulgular; düzeltme yetkisi varsa sınırında devam |
| “Commit/PR akışını tamamla” | [yorunge-pr](skills/yorunge-pr/SKILL.md) | Development hedefli doğrulanmış PR/merge durumu |

Küçük yazım düzeltmesini altı skill'lik törene çevirme. Bütün kataloğu yükleme; yalnız görevi ve kritik değişen sınırı karşılayan skill'i oku. Yetkilendirilmiş uygulama talebini plan skill'inin durma kuralıyla yarım bırakma. Önceki turda başlamış iş yeni bir planlama projesi değildir.

## Gereken bağlam

- Config/context için mevcut modeller + identity-context modülü + config/CLI referansı.
- Capability/plan/state için capability kaydı + execution/data-and-state + ilgili P01 kartı.
- Native veri/çıkarım için ilgili modül + güncel resmî hizmet sözleşmesi; eğitim araçlarını gereksiz yükleme.
- Tool/execution için provider sözleşmesi + ayrı ortam/görev matrisi + sonuç/artefakt kabulü.
- Belge/roadmap için yalnız ilgili faz/karar/kanıt ve belge standardı; tasarım ile implementasyonu karşılaştır.

Komutlar ve hangi değişiklikte hangisinin gerekli olduğu [CONTRIBUTING](../CONTRIBUTING.md#doğrulama-seçimi) içinde tek yerde tutulur. Hazır işin kabulünü tekrar icat etme; büyük faz satırını da hazır kart sayma.

[Epik PR sözleşmesi](../docs/roadmap/README.md#epik-başına-pr) ve [P01-2 paket planı](../docs/roadmap/p01-2-delivery-plan.md) aynı PR'daki alt adımların sırasını belirler. Alt kartın gerçek commit/test/review kanıtı sonraki adımın önkoşuludur; bağımsız PR/merge zorunluluğu değildir. Hazırlık araştırması ve Proposed ADR ürün uygulaması sayılmaz.

## Yerleşim ve keşif

Kanonik skill dosyaları `.agents/skills/<name>/SKILL.md`; Codex UI metadata'sı aynı skill'in `agents/openai.yaml` dosyasındadır. Claude Code için `.claude/skills/<name>` göreli bağlantıları aynı kanonik klasöre gider. Böylece iki istemci için iki içerik kopyası oluşmaz. [CLAUDE.md](../CLAUDE.md) ortak kurala yönlendirir. Kullanıcı/global ayar, izin listesi, MCP bağlantısı, hook veya sabit model seçimi eklenmez.

Codex'te `$yorunge-plan-task`, Claude Code'da `/yorunge-plan-task` örnek açık çağrıdır; açıklama uygun olduğunda otomatik seçim de mümkündür. Keşif davranışının kaynakları: [OpenAI yerel skills](https://learn.chatgpt.com/docs/build-skills) ve [Claude Code project skills/symlink desteği](https://code.claude.com/docs/en/skills) (erişim 2026-10-27). Bu repo kontrolü metadata/link/alias yapısını doğrular; her istemci sürümünde UI seçim testi yapıldığı anlamına gelmez. Görünmüyorsa yeni oturum/istemci yeniden yüklemesiyle kontrol et.

Kanonik kılavuzlar sdist geliştirme kaynağına dahildir; wheel runtime'ına dahil değildir. Claude alias'ları yalnız repo entegrasyonudur, sdist'te symlink olarak yayımlanmaz. Tam ajan doğrulaması Git checkout'unda çalışır.

Tam geliştirme/test ortamı gerçek symlink destekleyen macOS/Linux checkout'udur; Windows'un symlink'i düz dosyaya çevirdiği checkout bu entegrasyonu sağlayamaz. Ortam ve doğrulama sınırı [CONTRIBUTING](../CONTRIBUTING.md#geliştirme-ve-doğrulama) içinde kayıtlıdır.

## Yetki ve devir

Skill bir talimat kaynağıdır, yeni dış işlem yetkisi değildir. Sıradan çalışma repo iznini/release'i değiştirmez; Master aktarımı kullanıcıdadır. Bağımsız ajan değerlendirmesi yalnız kullanıcı veya geçerli çalışma yönergesi yetkilendirmişse yapılır; bir skill'in varlığı delegasyon izni değildir.

Devirde iş ID/kapsamı, dal/commit, değişen sözleşme, gerçek test/ölçüm ve kalan engel yeterlidir. Özel çalışma arşivini bağlama, paket veya yayın girdisine ekleme. İnceleme ve kanıt kaydı [hazırlık review'sinde](../docs/research/roadmap-readiness-review.md) tutulur.
