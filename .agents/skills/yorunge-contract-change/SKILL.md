---
name: yorunge-contract-change
description: Yörünge CLI, Python API, TOML/YAML, capability veya hizmet/araç sözleşmesini değiştirirken şema, tüketici, hata ve belge uyumunu koru. İç uygulama refaktörü ve sadece biçim düzeltmesi için kullanma.
---
# Yörünge sözleşmesini değiştir

Önce ilgili [kanonik referansı](../../../docs/reference/README.md), mevcut modeli ve tüketici testini bul. `src/yorunge/domain/models.py` bugünkü dar şemadır; tasarlanan provider/execution portları henüz uygulanmış sayılmaz.

1. Önce/sonra davranışını ve uyumluluk etkisini yaz. Alanın kaynağı, tip/sürüm, default/override ve bilinmeyen alan davranışını belirle. Kamuya açık seçim, güven sınırı veya temel kararı değiştiriyorsan uygun ADR'yi kaydet; rutin teknik tercihi gereksiz onay döngüsüne çevirme.
2. Alanın gerçek tüketiciye ulaştığını izle: parse → domain/application → adaptör/yüzey. Yalnız modele alan eklemek teslim değildir. Desteklenmeyen ayarı düşürme; eksik araç veya ortamda fallback yapma.
3. İlgili hata sınırlarını gerçek parser/taşıma/süreçte sına: duplicate/yanlış tip/sürüm, sonlu olmayan sayı, malformed yanıt, sır sızıntısı veya yarım çıktı. Değişiklikle ilgisiz bütün güvenlik testlerini zorunlu hale getirme.
4. Plan ve capability için hedef/yetki/araç/sürüm/ortam kapsamını koru. Saved plan mevcut profilden yeniden seçilmez. Yalnız şema doğrulamasını uzak erişim, `supported`, yürütme veya artefakt kanıtına yükseltme.
5. Kanonik sözleşmeyi, gerekiyorsa örneği ve CLI/Python tutarlılık testini aynı değişiklikte güncelle. Migration/deprecation gerekiyorsa veri kaybı ve eski sürüm yolunu açıkla.

Çıktı: sözleşme farkı, tüketici etkisi, kanıt ve henüz desteklenmeyen kapsam. Adaptör değişikliğinde [araç sözleşmesini](../../../docs/reference/tool-provider-contract.md), kimlik/state değişikliğinde [execution bağlarını](../../../docs/architecture/execution-model.md) ayrıca oku.
