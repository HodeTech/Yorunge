---
name: yorunge-plan-task
description: Yörünge faz maddesini kapsam, bağımlılık ve ölçülebilir kabulle dar bir iş paketine dönüştür. Plan/scope ve işe hazırlık taleplerinde kullan; salt review, küçük yazım düzeltmesi veya zaten sınırları belli uygulama için kullanma.
---
# Yörünge işini planla

[AGENTS.md](../../../AGENTS.md) okuma sırası geçerlidir. Önce [current](../../../docs/roadmap/current.md), ilgili faz ve mevcut iş kartını oku; bütün dokümanları yeniden bağlama yükleme.

1. Kullanıcının istediği sonucu faz ID'sine bağla. [Planlama sözleşmesindeki](../../../docs/roadmap/README.md#hazır-iş-paketi) ready koşullarını gerçek kod/kanıt üzerinden kontrol et; üst fazın planlanmış olması bağımlılığın tamamlandığı anlamına gelmez.
2. Tek gözden geçirilebilir sonuç seç: giren ve dışarıda kalan işler, görev/araç/hizmet/ortam, değişecek sözleşmeler ve doğrulama. Büyük satırı alt ID'lere ayır; mevcut ID'leri yeniden numaralandırma.
3. Açık karar veya dış erişim gerekiyorsa onu ayrı araştırma/karar çıktısı yap. Kullanıcının mevcut kararını yeniden onaya götürme; gerçek bir ürün tercihi eksikse bağımsız planlama işlerini sürdürerek eksikliği belirt.
4. Anlamlı yeni uygulama dilimi için [iş kartı şablonunu](../../../docs/roadmap/task-template.md) kullan; aynı kabul listesini faz ve current'a kopyalama. Rutin düzeltmeye yeni kart/ADR zorunluluğu ekleme.
5. Kabulü gözlenebilir yap: olumlu sonuç, tehlikeli hata yolu, gerekli kaynak bütçesi ve kanıtın nerede oluşacağı. Geçmiş test sayısı veya hedef tarih tek başına kabul değildir.

Çıktı: ID, kullanıcı sonucu, kapsam sınırı, bağımlılıklar, planlama büyüklüğü, kabul/doğrulama ve açık koşullar. Yalnız plan istenmişse burada bitir; aynı istekte uygulama da yetkilendirilmişse planı uygulamaya bağla. Planın yazılması ürünü `verified` yapmaz.
