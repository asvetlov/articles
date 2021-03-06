Title: Графический интерфейс, часть третья
Authors: Andrew Svetlov
public_url: http://asvetlov.blogspot.com/2011/02/blog-post_08.html


В предыдущих частях [1](http://asvetlov.blogspot.com/2011/02/blog-post_05.html) 
и [2](http://asvetlov.blogspot.com/2011/02/blog-post_05.html)
были рассмотрены проблемы, 
стоящие перед разработчиком пользовательского интерфейса. 

Настала пора переходить к решениям.

Сразу скажу: полного и хорошего ответа я не знаю.


Простое решение номер один: _Model-View-Presenter_
---------------------------------------------------

Мартин Фаулер обратил внимание на проблемы парадигмы
_Model-View-Controller_ довольно давно. 

Советую почитать его статью 
[GUI Architectures](http://martinfowler.com/eaaDev/uiArchs.html),
в которой подведен итог размышлений о различных подходах 
к созданию пользовательского интерфейса. Помимо всего прочего статья содержит
много ссылок на используемые её автором _шаблоны проектирования_, ознакомится
с которыми полезно.

За несколько лет предложенный Фаулером шаблон _Model-View-Presenter_ усложнился
и эволюционировал, далеко уйдя от первой (весьма наивной) реализации.

И всё же имеет смысл начинать именно с неё.

1. Есть _модель предметной области (Domain Model)_. 
    В ней сконцентрированы бизнес-логика, 
    взаимодействие с базами данных и прочие полезные вещи.

2. _Форма GUI_ или _вид (View)_ отображает эту модель (или её часть) 
    в виде своих виджетов.

3. _Представление (Presenter)_ осуществляет связь между _моделью_ и _видом_, 
    реагируя на события пользователя и обновляя _вид_ в ответ на изменения _модели_.

_Модель_ содержит все данные, необходимые для работы _вида_. 

Например, если _форма_ имеет _поле ввода_, 
которое может быть запрещено для редактирования
и должно изменять свой цвет в зависимости от состояния, то модель должна иметь 
атрибуты:

* `value_text`, _read-write_

* `value_enabled`, _readonly_

* `value_color`, _readonly_

_Представление_ подписывается на события _вида_. В ответ на изменение пользователем
текста в поле ввода (или при нажатии кнопки "применить", поведение зависит от
используемого сценария работы) _представление_ берет текст, содержащийся 
в _поле ввода_ и записывает его в _модель_. 
Если был выбран сценарий с кнопкой "применить" - вызывается соответствующий 
метод _модели_.

Затем _представление_ обновляет _вид_, приводя _поле ввода_ в соответствии
с `value_text`, `value_enabled` и `value_color`.

Более сложный сценарий взаимодействия будет в том случае, если отображаемое 
значение модели может изменятся вне нашей формы (например, другой открытой формой 
приложения).

Для таких сценариев _представление_ должно выступать в роли _наблюдателя (Observer)_
для интересующих частей модели, приводя _вид_ в соответствие _модели_ при каждом
изменении последней.

_Вид_ практически не содержит иного кода, кроме требуемого для создания виджетов
формы. Часто этот код может быть полностью сгенерирован средством автоматического
создания интерфейса, и это хорошо.

Комплексные модели
------------------

Современные программы обычно имеют довольно сложную структуру предметной области.
Модели вкладываются друг в друга, а формы отображают их в различных нетривиальных
виджетах (деревья, списки и т.д.)

Для работы с такими моделями _представления_ *обязаны* быть _наблюдателями_, 
одновременно выступая _адаптерами_ для виджетов.

Это требуется хотя бы потому, что полное обновление комплексного виджета
(например, таблицы) при изменении лишь малой его части (строки или ячейки)
может занимать неоправданно большое время и вести к неприятным побочным эффектам.

При хорошем проектирования часто удается обойтись несколькими _адаптерами_
общего назначения, агрегируя их в _представлении_ и настраивая характер связей
между _адаптером_ и _моделью_, но это получается далеко не всегда.

Следование сложным сценариям работы может потребовать создания множества 
различных адаптеров для каждой новой формы.


Тестирование
------------

Разнесение _вида_ и _модели_, проведение взаимодействия между ними только через
_представление_ очень помогает при создании автоматических тестов.

Во первых, _модели_ могут и должны работать независимо от _представлений_
(и, тем более, _видов_). Значит и тестировать их можно независимо.

По вторых, можно создавать тестовые виды, содержащие все необходимые 
для представления атрибуты - но не являющиеся виджетами. Т.е. тестирование
_представлений_ может быть проведено без создания форм _GUI_.


Недостатки
----------

Куда ж без них?

Во первых, приходится писать довольно много рутинного и однообразного кода 
в _представлениях_. Правильно выбранная архитектура, декомпозиция представлений
на агрегирируемые вспомогательные классы 
(синхронизатор поля ввода с изменяемым цветом, например - и т.д.) - неплохо помогают,
но проблема всё же временами дает о себе знать.

Более того, использование агрегируемых синхронизаторов усложняет диагностику
возникающих ошибок - тут уж ничего не поделаешь.

Во вторых, _модели_ должны быть спроектированы в таком виде, чтобы любое их значимое
изменение порождало события, попадающие в _представления_ и вызывающие обновления
нужных видов.

Это тоже требует дополнительного кодирования.

Есть и более серьёзные проблемы.

Изменение модели может порождать изменение вида, которое в свою очередь опять
меняет вид - и так до бесконечности. Выявление и предотвращение таких циклов 
не всегда легкое и очевидное дело.

Часто бывает, что модель нужно менять в рамках одной или нескольких транзакций:
сначала перенести значения из виджетов в модель, затем выполнить какие-то действия
и лишь после всего обновить вид. Это тоже решается путем усложнения синхронизирующего
кода представлений.

Заключение
----------

Предложенная схема организации _модель-вид-представление_ обладает очевидными
достоинствами.

Это, в первую очередь, четкое разделение модели предметной области и графического
интерфейса с прописыванием их синхронизации в едином месте - представлении.

При помощи рассмотренного подхода можно создавать интерфейсы любой степени сложности.

Значительно облегчается автоматическое тестирование.

Вместе с тем я перечислил и недостатки. Они не фатальны, но требуют внимательности
и дисциплины при проектировании приложения.

Недостатки вызваны, на мой взгляд, не порочностью самого подхода - 
а его низкоуровневостью. Т.е. на предлагаемой основе можно строить более
сложные концепты, автоматизирующие задачи по синхронизации модели и вида
в представлениях и позволяющие сконцентрировать усилия на предметной области.



Небольшое отступление. 
----------------------

Я очень люблю книгу Мартина Фаулера "Refactoring". Купите - не пожалеете.

Помимо очень хороших рекомендаций по улучшению кода этот справочник имеет 
еще одну крайне полезную функцию. 

Если вы чуете пятой точкой, что нужно сделать
так а не иначе - откройте Refactoring и найдите нужное вам изменение.
Покажите страницу начальнику или коллегам. Вероятно, авторитет Мартина позволит вам
протолкнуть собственную точку зрения.

Соблюдайте осторожность! Если коллеги внимательно читали принесенную вами в качестве
последнего довода книгу - они с легкостью найдут в ней противоположный рецепт.

В любом случае открытое обсуждение "дурных запахов" если 
и не поможет вам настоять на своем - то позволит еще раз проговорить 
сложные архитектурные места, отчетливей проявить позицию сотрудников,
достичь взаимопонимания хотя бы в элементарных терминах
и вообще - здорово провести время.


