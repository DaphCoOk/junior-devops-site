/* Это объявление переменной, мы наши кнопку по тегу */
const button = document.querySelector('button');

/* Тут на кнопку навешиваем обрабочик, который ждёт клика и тогда запустит логику */
button.addEventListener('click', function() {
	alert("Można się ze mną skontaktować mailowo: Ustenkoillia29@gmail.com lub telefonicznie: +48 577-924-758")
})