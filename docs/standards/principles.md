# Ürün ve mühendislik ilkeleri

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

1. **İşi tamamlat.** Her özellik bir kullanıcı sonucu, hata/toparlanma yolu ve kabul ölçütüyle tanımlanır. API ucunu sarmalamak tek başına fayda kanıtı değildir.
2. **Kolay başlangıcı koru.** Makul varsayılanlar ve doğru aşamada gösterilen seçenekler kullanılır. İleri kullanıcı açık argüman/JSON ile aynı işi yapabilmelidir.
3. **Platform kapsamını koru.** Yörünge EVREN yaşam döngüsünü kapsar; uygun LLM görevlerinin varsayılan aracı ForgeLM'dir. Diğer görevler gereksiz eğitim bağımlılığı taşımaz.
4. **Seçimi dürüst uygula.** Araç ve ortam değişimi açık; desteklenmeyen parametreler görünür; sessiz fallback yoktur.
5. **Performansı baştan tasarla.** Bellek, başlangıç, istek sayısı, eşzamanlılık ve bekleme bütçesi özellik kabulünün parçasıdır.
6. **Doğruluğu hızla takas etme.** Eski manifest, önbellek veya günlük kaydı güncel içerik/uzak sonuç kanıtının yerine geçmez.
7. **Durumu kalıcı tut.** Etkili işlem kimliği, plan ve belirsizlik yeniden başlatmada kaybolmamalıdır.
8. **Kanıtın sınırını göster.** Tasarım, uygulama, yerel test, canlı hesap ve yayımlanmış destek ayrı statülerdir.
9. **Tek kanonik sözleşme kullan.** CLI/Python/MCP iş mantığını çoğaltmaz; config ve çıktı şeması tek yerde tanımlanır.
10. **Gerektiği kadar yapı kur.** Yerel bir istemci için sunucu kümesi, bulut kontrol düzlemi veya genel eklenti pazarı başlangıç bağımlılığı değildir.

Çelişki olduğunda kullanıcı sonucunu ve ölçülen etkiyi açıklayan küçük bir karar kaydı hazırlanır. Bir standardın bütün maddelerini aynı anda uygulayan büyük refaktör, kendi başına kullanıcı değeri sayılmaz.
