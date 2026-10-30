# AGENTS.md — Desarrollo de Aplicaciones con Objetos

## 1. Propósito

Este repositorio contiene actividades y proyectos de **Desarrollo de Aplicaciones con Objetos (DAO)** de Ingeniería en Sistemas de Información — UTN Facultad Regional Córdoba.

Este archivo establece instrucciones permanentes para los agentes que trabajen sobre el repositorio. Debe evolucionar a medida que la cátedra publique material nuevo.

---

## 2. Fuente de autoridad

Respetar este orden de prioridad:

1. Enunciado específico de la actividad.
2. Indicaciones explícitas del docente.
3. Material oficial de la cátedra correspondiente al tema.
4. Este `AGENTS.md`.
5. Convenciones existentes y coherentes del repositorio.
6. Buenas prácticas generales de Python e ingeniería de software.

Una buena práctica general no debe reemplazar una decisión pedagógica de la cátedra. Si existe una contradicción relevante, informarla antes de tomar una decisión irreversible.

---

## 3. Alcance académico actual

El material oficial disponible comprende:

* fundamentos de Python y programación estructurada;
* tipos de datos, operadores, condicionales, truthiness, ciclos, funciones y secuencias;
* cadenas, tuplas y listas;
* programación funcional, funciones como valores y funciones de orden superior;
* funciones `lambda`, comprensiones, `map()`, `filter()` y `reduce()`;
* archivos de texto y binarios, persistencia, lectura y escritura;
* procesamiento manual de archivos delimitados;
* conjuntos y diccionarios;
* excepciones y gestión de errores;
* clases, objetos, atributos, constructores, referencias y métodos;
* encapsulamiento y propiedades;
* métodos mágicos de representación, comparación y aritmética;
* relaciones entre objetos, composición, agregación y cardinalidad;
* herencia, especialización, constructores de clases derivadas y uso de `super()`;
* polimorfismo y sobreescritura de métodos;
* clases y métodos abstractos e interfaces mediante `ABC` y `@abstractmethod`;
* testing unitario con `pytest`, aserciones, excepciones esperadas, aproximación y parametrización;
* patrones de diseño: Singleton, Factory, Observer, State, Strategy e Iterator;
* protocolo de iteración de Python: `__iter__()`, `__next__()` y `StopIteration`;
* acceso a SQLite con `sqlite3`, conexiones, cursores y sentencias SQL;
* operaciones de Alta, Baja, Modificación y Consulta (ABMC), recuperación de resultados y transacciones;
* generación de reportes: documentos PDF con ReportLab, gráficos con Matplotlib incorporados al PDF y archivos CSV con el módulo estándar `csv`;
* consigna del TP Integrador 2026, Tema 3 (sección 16).

Un concepto abordado no es obligatorio en todas las actividades: comprobar el tema y nivel del ejercicio. Las interfaces de métodos no son interfaces gráficas, que no están desarrolladas en el material de la cátedra.

---

## 4. Progresión académica

* Utilizar únicamente conceptos compatibles con la actividad.
* No introducir objetos en ejercicios destinados a practicar programación estructurada, archivos o colecciones.
* Utilizar objetos cuando la actividad evalúe modelado con clases.
* No introducir herencia, polimorfismo, patrones, arquitecturas o librerías externas antes de que sean necesarios o abordados.
* No ocultar con abstracciones avanzadas la lógica que el estudiante debe comprender y explicar.

Una solución académicamente adecuada tiene prioridad sobre una solución innecesariamente sofisticada.

---

## 5. Flujo general de implementación

Antes de editar:

1. Leer el enunciado, los `AGENTS.md` aplicables y los archivos relevantes.
2. Inspeccionar la implementación existente.
3. Identificar el concepto que practica la actividad.
4. Mantener las decisiones correctas ya presentes.
5. Realizar solo los cambios necesarios.

Evitar refactorizaciones ajenas al alcance. No cambiar nombres, estructura o comportamiento por preferencia personal si son correctos y coherentes.

---

## 6. Convenciones confirmadas

Aplicar cada regla o contrato al concepto que evalúa la actividad. Distinguir las variantes observadas (sección 7) y los complementos generales (sección 9.1). La sección 15 identifica las fuentes.

### 6.1 Booleanos, truthiness y rangos

Preferir `if existe:` e `if not existe:` frente a comparaciones redundantes con `True` o `False`.

Utilizar truthiness cuando exprese claramente la intención, por ejemplo con cadenas o colecciones vacías. No usarla si vuelve ambigua la condición.

Puede utilizarse la comparación encadenada para una misma variable:

```python
if 0 < nota <= 10:
    ...
```

### 6.2 Validaciones y funciones

Respetar todas las restricciones de entrada. Impedir que datos inválidos continúen cuando el enunciado lo requiera y no eliminar validaciones correctas.

Utilizar funciones para separar tareas coherentes, reutilizar procesamiento o simplificar el flujo principal. Evitar fragmentar innecesariamente ejercicios pequeños.

### 6.3 Programación funcional

Las funciones pueden almacenarse en variables, recibirse como parámetros y devolverse.

Si el enunciado solicita programación funcional, comprensiones o una función de orden superior concreta, conservar esa herramienta. No reemplazarla por otro enfoque que elimine el concepto evaluado.

Limitar las funciones `lambda` a expresiones breves. Importar `reduce()` desde `functools`.

### 6.4 Archivos

* Elegir el modo según la operación requerida: `r`, `w`, `x`, `a`, `r+` y variantes binarias.
* Recordar que `w` crea o trunca, `x` impide sobrescribir y `a` conserva y agrega al final.
* Cerrar siempre el archivo y mantenerlo abierto solo el tiempo necesario.
* No esperar entrada del usuario con un archivo abierto si no hace falta.
* Elegir `read()`, `readline()`, `readlines()` o recorrido directo según el tamaño y procesamiento.
* Recordar que `write()` y `writelines()` no agregan saltos de línea.

Si la actividad busca practicar el procesamiento manual de datos delimitados, no sustituirlo automáticamente por `csv`, `pandas` u otra librería. El módulo `csv` corresponde a la generación de reportes (sección 6.25), no a los ejercicios de archivos que evalúan el procesamiento manual.

### 6.5 Conjuntos

Usar conjuntos cuando se necesiten elementos únicos, pertenencia eficiente u operaciones de conjuntos.

No acceder por índice ni asumir un orden. Si se requiere orden, obtener una secuencia con `sorted()`.

Distinguir los métodos que crean un resultado nuevo —`union()`, `intersection()`, `difference()`, `symmetric_difference()`— de las variantes que modifican el conjunto original.

### 6.6 Diccionarios

Usar diccionarios cuando exista una asociación natural entre una clave única y un valor.

Elegir conscientemente entre:

* `diccionario[clave]`: produce `KeyError` si no existe;
* `get()`: devuelve `None` o un valor predeterminado;
* `setdefault()`: además crea la entrada predeterminada si no existe.

Recorrer con `keys()`, `values()` o `items()` según se necesiten claves, valores o pares. Los pares de `items()` pueden desempaquetarse en el `for`.

### 6.7 Excepciones

Distinguir entre capturar con `try`/`except` para informar, corregir o brindar una alternativa, y disparar con `raise` al detectar una condición errónea.

Usar `else` para código que solo debe ejecutarse sin excepción y `finally` para código que debe ejecutarse siempre.

Una excepción propia debe ser una clase derivada de `Exception`. No crearla si el dominio o el ejercicio no la necesita.

### 6.8 Clases, referencias y métodos

En actividades orientadas a objetos:

* modelar objetos con estado y comportamiento relacionados;
* inicializar el estado requerido en `__init__`;
* recibir como primer parámetro de cada método de instancia la referencia al receptor, denominada `self` por convención;
* acceder al propio estado y comportamiento mediante `self`;
* enviar mensajes mediante una referencia, el operador punto y el método;
* comprobar que una referencia no sea `None` antes de enviarle un mensaje cuando pueda estar vacía.

Asignar una referencia a otra variable no duplica el objeto: ambas referencian la misma instancia. Para crear otra instancia se invoca el constructor.

### 6.9 Encapsulamiento y propiedades

Los objetos deben proteger su implementación y mantener válido su estado. Otros objetos deben colaborar mediante la interfaz pública, sin depender innecesariamente de la representación interna.

Cuando un dato requiera validación, cálculo u ocultamiento, utilizar `@property` y, si corresponde, su `setter`, respaldados por un atributo interno como `_documento`.

No crear automáticamente propiedades triviales para todos los atributos. Las validaciones que protegen un estado pertenecen al objeto responsable de ese estado.

### 6.10 Métodos mágicos

Implementarlos solo con semántica clara en el dominio:

* `__str__` para una representación textual relevante;
* `__eq__`, `__ne__`, `__lt__`, `__gt__`, `__le__` y `__ge__` para comparaciones;
* `__add__`, `__mul__` u otros métodos aritméticos cuando la operación tenga sentido.

No inventar criterios de igualdad, orden u operaciones sin respaldo en el enunciado o dominio.

`__iter__` y `__next__` pertenecen al protocolo de iteración y se tratan en la sección 6.24.

### 6.11 Composición, agregación y cardinalidad

Antes de implementar una relación “todo/parte”, determinar su naturaleza y cardinalidad.

**Composición:** la parte pertenece exclusivamente a un contenedor, carece de sentido independiente y su ciclo de vida está ligado a él. El contenedor controla la creación y eliminación de sus partes y no debe permitir transferirlas.

**Agregación:** el objeto relacionado posee identidad y ciclo de vida propios, puede existir sin el contenedor y puede migrar. El método de agregado puede recibir una instancia externa y el de remoción puede devolverla.

Python implementa ambas con referencias: la diferencia es semántica y de diseño, no sintáctica.

Para decidir, preguntar:

1. ¿La parte podría pasar a otro contenedor del mismo tipo?
2. ¿Tiene sentido que exista sin ningún contenedor?

Una respuesta afirmativa apunta a agregación. Si ambas son negativas, apunta a composición.

Para la cardinalidad:

* usar referencias simples para una cantidad fija y pequeña;
* usar una colección para una cantidad variable, grande o desconocida;
* inicializar vacía en el constructor la colección perteneciente al contenedor, salvo indicación contraria;
* programar como métodos del contenedor las responsabilidades que involucran la colección;
* no exponer indiscriminadamente la colección interna.

En composición, un método de remoción no debe devolver la parte; puede no devolver nada o informar con un booleano. En agregación, devolverla es coherente si debe conservarse o transferirse.

### 6.12 Herencia y especialización

La herencia relaciona una clase base o superclase con una clase derivada o subclase. La derivada hereda estructura y comportamiento y puede agregar o redefinir miembros.

* Comprobar la relación con la frase «un objeto de la derivada ES UN objeto de la base». No usar herencia para una relación todo/parte, como Auto/Rueda.
* Declarar la base en la cabecera: `class Derivada(Base):`.
* Acceder mediante `self` a los atributos y métodos heredados. No usar `super()` indiscriminadamente para cualquier miembro de la base.
* Utilizar `super()` cuando una redefinición necesita apoyarse en la implementación heredada, por ejemplo en `__init__` o `__str__`.
* Si se redefine `__init__`, invocar explícitamente la inicialización necesaria de la base y reenviar los parámetros que le correspondan: no se ejecuta automáticamente.
* Invocar el mismo método con `self` desde su redefinición produce recursión, no una llamada a la base.

No duplicar mediante copia y pegado el comportamiento común que la jerarquía debe reutilizar. Tampoco crear una jerarquía solo porque dos clases tengan algunos atributos similares.

### 6.13 Polimorfismo y sobreescritura

Sobreescribir un método consiste en definir en la derivada un método con el mismo nombre que uno heredado para brindar comportamiento propio.

En una actividad de polimorfismo, enviar el mismo mensaje a objetos que cumplen un contrato común: la implementación depende del receptor. No reemplazarlo con cadenas de `if` o `isinstance()` que seleccionen manualmente el comportamiento por clase.

Esto no prohíbe `isinstance()` en validaciones justificadas o aserciones de pruebas.

Conservar el comportamiento heredado cuando sea correcto. Al extenderlo, reutilizarlo con `super()` en vez de repetir su implementación.

### 6.14 Clases abstractas e interfaces

* Utilizar `ABC` y `abstractmethod` del módulo estándar `abc` cuando el modelado requiera un contrato abstracto explícito.
* Una clase con métodos abstractos pendientes no puede instanciarse. Las clases concretas deben implementar los métodos abstractos necesarios para cumplir el contrato.
* Una clase abstracta puede reunir comportamiento común concreto y operaciones abstractas.
* En el enfoque del material, una interfaz se representa mediante una ABC compuesta por métodos abstractos: especifica los servicios, no su implementación.
* Clases de dominios distintos pueden implementar la misma interfaz y ser utilizadas uniformemente sin conocer sus tipos concretos.

Está abordada la implementación de varias interfaces, no la introducción automática de herencia múltiple concreta ni de jerarquías complejas.

### 6.15 Testing unitario con pytest

Las pruebas unitarias verifican comportamientos de funciones, métodos o clases de forma aislada. Deben ser rápidas, independientes, repetibles y claras respecto de lo que comprueban.

Cuando corresponda trabajar con el framework presentado:

* Utilizar `pytest` y aserciones estándar `assert` para comprobar resultados, estado observable y comportamiento esperado.
* Para el descubrimiento automático, respetar archivos `test_*.py` o `*_test.py` y funciones cuyo nombre empiece con `test_`, salvo configuración existente que indique otra cosa.
* Dar nombres descriptivos a las pruebas y cubrir casos normales, límites y errores aplicables al enunciado.
* Comprobar excepciones esperadas mediante `pytest.raises()`; verificar su mensaje cuando sea parte del requisito.
* Utilizar `pytest.approx()` cuando la comparación requiera tolerancia por representación de punto flotante. Respetar un criterio de redondeo explícito del ejercicio.
* Si se parametriza una prueba, utilizar `@pytest.mark.parametrize` con entradas y resultados esperados coherentes.
* No permitir que una prueba dependa del estado dejado por otra.

Distinguir pruebas aisladas de integración. Comprobar requisitos y responsabilidades, sin inventar reglas a partir de la implementación.

Pytest es una dependencia externa abordada: puede usarse en estas actividades, sin habilitar otros paquetes automáticamente.

### 6.16 Patrones de diseño

Un patrón es una solución general a un problema recurrente de diseño; permite reutilizar conocimiento, no exige copiar una implementación literal.

Antes de aplicarlo, identificar el problema, el contexto de uso, los objetos y relaciones de la solución y sus consecuencias. Justificar su correspondencia con la actividad. No introducir patrones únicamente porque estén disponibles en el material.

La guía de patrones de comportamiento reconoce que, en ejemplos pequeños, los condicionales también funcionan: el patrón resulta especialmente útil cuando crecen los estados, algoritmos u operaciones. Esa evaluación forma parte de la justificación.

### 6.17 Singleton

Singleton busca garantizar una única instancia y proporcionar un punto de acceso a ella. Usarlo solo cuando esa unicidad responda a una necesidad real del ejercicio.

En la variante con `__new__`, este controla la creación y devuelve la instancia conservada en un atributo de clase. `__init__` inicializa el objeto y puede ejecutarse nuevamente aunque se devuelva la misma instancia.

Evitar que accesos posteriores reinicialicen o borren el estado compartido. Verificar la unicidad por identidad, por ejemplo con `is`, no solo por igualdad de valores.

No imponer una variante única. Considerar el acoplamiento global y el estado compartido entre pruebas; el ejemplo de un gestor no obliga a convertir toda conexión SQLite en Singleton.

### 6.18 Factory

La variante desarrollada en las filminas utiliza un método de creación redefinido por fábricas concretas y productos que cumplen un contrato común; corresponde al enfoque de Factory Method.

Cuando se solicite esa variante:

* identificar el contrato del producto y el de la fábrica;
* hacer que cada fábrica concreta cree y devuelva el producto concreto correspondiente;
* concentrar la selección e instanciación del producto en la fábrica;
* utilizar los productos mediante su contrato común, sin que el consumidor tenga que conocer su clase concreta.

No presentar un helper o condicional como equivalente a la estructura evaluada sin justificarlo, ni introducir otros patrones no solicitados.

### 6.19 Observer

Observer permite notificar cambios de un sujeto a los observadores suscriptos mediante una interfaz común.

* El sujeto mantiene las referencias a sus observadores y realiza la notificación.
* Los observadores implementan el contrato de actualización.
* La comunicación no debe depender de conocer cada clase concreta de observador.
* Relacionar sujeto y observadores mediante referencias y suscripción, no herencia entre ellos. Las bases e interfaces del patrón sí pueden utilizarse.

Respetar los cambios y datos que deben notificarse según el ejercicio. No agregar mensajería, eventos asíncronos ni servicios externos para el ejemplo académico.

### 6.20 State y Strategy

Ambos patrones utilizan un contrato común y un contexto que delega comportamiento, pero resuelven necesidades distintas:

* **State:** el comportamiento depende del estado interno del objeto. El contexto conserva el estado actual y delega en él; las transiciones corresponden a la lógica del contexto o de los estados, según el modelado del ejercicio.
* **Strategy:** encapsula algoritmos o políticas intercambiables. El cliente o una configuración externa selecciona la estrategia; el contexto delega en ella, sin decidir transiciones entre estrategias.

Identificar estados y transiciones en State, o algoritmos alternativos y su contrato en Strategy. No elegirlos únicamente por la semejanza de sus diagramas. La guía de patrones resume la diferencia con dos preguntas: Strategy responde «¿qué algoritmo utilizo?»; State, «¿qué puede hacer el objeto ahora?».

Mantener las reglas de cambio de comportamiento en el responsable correspondiente. No trasladar al cliente cadenas de condicionales que anulen la delegación que pretende practicar el ejercicio.

#### 6.20.1 Precisiones de la guía sobre State

* El contexto guarda una **referencia a un objeto estado**, no el nombre del estado en un string. `Pendiente()` crea un objeto aunque la clase no declare `__init__`: usa el inicializador heredado de `object`.
* El contexto delega pasándose a sí mismo: en `self.estado.avanzar(self)` el primer `self` es el contexto, receptor de `avanzar()`; dentro del estado, `self` es el estado y el parámetro recibido es el contexto.
* El estado recibe el contexto porque necesita solicitarle el cambio de estado mediante un método del contexto, como `cambiar_estado()`.
* Una transición reemplaza la referencia del contexto; el contexto sigue siendo el mismo objeto. La operación no devuelve el nuevo estado con `return`: su efecto es modificar el atributo del contexto.
* Cada estado decide qué operaciones permite y qué transición produce. Definir explícitamente qué ocurre ante una operación no permitida en ese estado (informar, ignorar o rechazar), según el enunciado.
* Un estado final puede responder sin producir transición.

#### 6.20.2 Precisiones de la guía sobre Strategy

* Cada algoritmo se encapsula en una clase que cumple el contrato abstracto; el contexto la recibe en el constructor y puede cambiarla mediante un método como `cambiar_estrategia()`.
* El polimorfismo aparece en la instrucción de delegación, por ejemplo `self.estrategia.calcular(precio)`: se ejecuta el método de la estrategia recibida sin preguntar su clase concreta.
* El patrón reemplaza la selección del algoritmo mediante `if`/`elif` dentro del contexto.

### 6.21 Acceso a SQLite y objetos de acceso

SQLite almacena la base en un archivo y se accede mediante el módulo estándar `sqlite3`; no requiere instalar un servidor para las actividades presentadas.

Distinguir las responsabilidades:

* `sqlite3.connect()` abre la conexión y puede crear el archivo si no existe.
* `Connection` administra el vínculo con la base y la transacción.
* `conexion.cursor()` crea un `Cursor`.
* `Cursor` ejecuta sentencias SQL y recupera sus resultados.

El comando SQL es un string de Python. Las triples comillas sirven para escribirlo en varias líneas; no forman parte de SQL.

Relacionar las operaciones ABMC con sus sentencias:

| Operación | Sentencia SQL |
| --- | --- |
| Alta | `INSERT` |
| Baja | `DELETE` |
| Modificación | `UPDATE` |
| Consulta | `SELECT` |

Respetar el esquema del enunciado, sin agregar ORM, servidores remotos ni capas complejas para practicar conexión, cursor y SQL directo.

### 6.22 SQL parametrizado y recuperación de resultados

Cuando los valores proceden de variables, utilizar parámetros `?` y entregar sus valores por separado, en el mismo orden, a `execute()`. No concatenarlos ni interpolarlos dentro del SQL.

* `execute()` ejecuta una sentencia SQL; `executemany()` permite repetirla con distintos conjuntos de parámetros.
* `fetchone()` recupera la siguiente fila o devuelve `None` si no quedan filas.
* `fetchall()` recupera todas las filas restantes, no vuelve al inicio del resultado.
* `fetchmany(size)` recupera un lote de filas.
* Por defecto, las filas se trabajan como tuplas. Distinguir la fila de los valores de sus columnas.

Seleccionar la recuperación apropiada al procesamiento. En un recorrido mediante `fetchone()`, actualizar la fila en cada iteración y terminar cuando sea `None`.

Para varias sentencias en un script, el método real es `executescript()`, no la grafía `executeScript()` del material. No sustituir con scripts operaciones que requieren parámetros.

### 6.23 Transacciones y errores de base de datos

Una transacción reúne cambios que deben tratarse como una unidad de trabajo. Determinar su alcance antes de ubicar las confirmaciones.

* `commit()` confirma los cambios de la transacción cuando la operación se completa correctamente.
* `rollback()` deshace cambios pendientes; no revierte cambios ya confirmados.
* Si varias modificaciones integran una misma acción, evitar confirmaciones intermedias que permitan guardar solo una parte de ella.
* No añadir `commit()` mecánicamente después de cada sentencia: una consulta `SELECT` no modifica datos.
* Considerar fallos y excepciones para evitar inconsistencias y liberar los recursos.

Cerrar recursos no equivale a confirmar la transacción. Identificar quién abre, confirma o revierte y cierra en cada operación.

### 6.24 Iterator y protocolo de iteración

Iterator permite recorrer una colección sin exponer cómo almacena sus elementos.

* En Python, el `for` utiliza el protocolo de iteración: `iter()` obtiene un iterador mediante `__iter__()` y `next()` obtiene el elemento siguiente mediante `__next__()`, hasta que se dispara `StopIteration`.
* La colección (por ejemplo `Biblioteca`) implementa `__iter__()` y devuelve un **objeto iterador nuevo** que recibe la referencia a los elementos y lleva su propia posición.
* El iterador (por ejemplo `IteradorLibros`) implementa `__iter__()` devolviendo `self` y `__next__()`, que devuelve el elemento actual, avanza la posición y dispara `StopIteration` al terminar.
* El código cliente recorre la colección con `for elemento in coleccion`, sin acceder directamente a la lista interna.
* Pueden existir varios iteradores para una misma colección, por ejemplo uno que entregue solamente los elementos que cumplen una condición. Cada iterador encapsula su criterio de recorrido.

Las listas de Python ya incluyen sus propios iteradores. Construir uno explícito tiene sentido cuando la actividad evalúa el patrón o cuando el recorrido debe ocultar la representación o aplicar un criterio propio. No convertir automáticamente toda colección en una clase iterable.

Iterator no habilita por sí mismo generadores (`yield`) ni el módulo `itertools`: no están desarrollados en la guía. No sustituir con ellos el iterador explícito cuando ese sea el concepto evaluado.

### 6.25 Reportes

El material de reportes presenta estas herramientas:

* **ReportLab** para generar documentos PDF con texto, tablas, imágenes y gráficos. Se instala con `pip install reportlab`.
* **Matplotlib** para generar el gráfico: ReportLab no lo construye por sí misma en el enfoque del material, sino que incorpora como imagen un gráfico creado con otra biblioteca.
* El módulo estándar **`csv`** para leer y escribir archivos CSV básicos. El material indica que es suficiente para ese uso; `pandas` solo se menciona para capacidades más avanzadas.

Al implementar un reporte:

* Separar la obtención y el cálculo de los datos de su presentación en PDF, gráfico o CSV.
* Un reporte consulta datos; no modifica el estado del sistema.
* Elegir el formato según el enunciado. No generar PDF o gráficos si la actividad solo pide calcular o mostrar resultados.
* Incorporar ReportLab y Matplotlib solo en actividades de reportes o cuando el enunciado lo requiera; son dependencias externas presentadas para ese fin, no habilitaciones generales.

---

## 7. Convenciones observadas

Estas prácticas aparecen en el material, pero no son exigencias universales sin respaldo del enunciado.

### 7.1 Función principal y punto de entrada

Es frecuente utilizar `principal()` y:

```python
if __name__ == "__main__":
    principal()
```

Aplicarlo cuando resulte compatible con el ejercicio y código existente.

### 7.2 Módulos e importaciones

Algunos ejemplos separan funciones o clases en módulos. Hacerlo solo cuando el tamaño o la actividad lo justifiquen.

También aparece `from modulo import *`; es una forma observada, no obligatoria. Respetar el enunciado y la forma coherente existente.

### 7.3 Gestión contextual de archivos

El material muestra cierre explícito y también:

```python
with open("datos.txt", "r") as archivo:
    ...
```

El administrador de contexto garantiza el cierre, pero no debe imponerse si se evalúan `open()` y `close()` explícitos.

### 7.4 Nombres y ubicación de clases

El material usa normalmente:

* sustantivos singulares en PascalCase para clases, como `CodigoPostal`;
* `self` para el receptor;
* un archivo por clase cuando la separación es útil, con nombre relacionado en minúsculas.

Conservar las convenciones coherentes del ejercicio. No reorganizar módulos para imitar un ejemplo aislado.

### 7.5 Nombres de interfaces y métodos de patrones

Los ejemplos usan el prefijo `I` (`INotificable`) y nombres como `factory_method`, `operation`, `attach`, `notify` y `update`. No obligan a usar inglés ni a renombrar el dominio; conservar los contratos y colaboraciones.

La guía de patrones de comportamiento usa nombres en español: `EstrategiaDescuento`, `calcular()`, `cambiar_estrategia()`, `EstadoPedido`, `avanzar()`, `cambiar_estado()` e `IteradorLibros`. Son ejemplos de nombres, no nombres obligatorios.

### 7.6 Organización y parametrización de pruebas

Se muestran suites por clase probada y agrupación opcional en clases como `TestNumeros`; no convertir todas las pruebas en métodos por ese ejemplo.

Las filminas muestran parametrización y comparaciones con redondeo; `semana-05.pdf` también desarrolla `pytest.approx()`. Elegir el criterio adecuado al requisito, sin imponer un formato de directorios o de tolerancia a partir de un único ejemplo.

### 7.7 Variantes de Singleton

El material explica el acceso mediante un método que conserva la instancia y muestra implementaciones Python con `__new__`. `semana-09.pdf` desarrolla además decoradores y una base abstracta con una instancia por subclase.

Seguir la variante indicada por el enunciado o docente; en su ausencia, conservar la implementación existente correcta o elegir la más simple que satisfaga el ejercicio. No imponer decoradores, una base reutilizable o metaclases solo para generalizar un Singleton pequeño.

Los nombres `_instance`, `_initialized` o `initialize` son ejemplos; cumplir la unicidad y conservar el estado sin exigir esos nombres.

### 7.8 Alternativas funcionales de State y Strategy

La sección 16.6 de `semana-09.pdf` admite funciones o callables en un diccionario cuando los comportamientos son sencillos, con una operación y sin estado interno complejo.

Esta alternativa no es obligatoria. No usarla para eliminar clases, interfaces o delegación explícita cuando esos sean los conceptos evaluados. Tampoco introducir una jerarquía innecesaria si el ejercicio admite el enfoque funcional mostrado.

### 7.9 Formas de acceso SQL mostradas

Los ejemplos utilizan SQL multilínea, `CREATE TABLE IF NOT EXISTS`, claves primarias, `fetchall()` con `for`, `fetchone()` con `while` y límites mediante `LIMIT ?`. Ninguna de esas elecciones es universal para toda actividad.

Los valores parametrizados se muestran en tuplas; para un único valor, `(valor,)` es una tupla, mientras que `(valor)` no lo es. Respetar el esquema requerido sin agregar automáticamente `AUTOINCREMENT` o reproducir nombres de tablas de ejemplo.

También se muestra captura de `sqlite3.Error` y cierre en `finally`. Un ejemplo con `except:` sin especificar el error no convierte la captura indiscriminada en una regla de la cátedra.

### 7.10 Formas de reporte mostradas

Los ejemplos de `Reportes en Python.pdf` construyen el PDF con el enfoque de flujo de ReportLab (`platypus`):

1. crear un `SimpleDocTemplate` con el nombre del archivo y el tamaño de página (`letter`);
2. acumular los elementos en una lista (`Paragraph`, `Spacer`, `Table`, `Image`);
3. obtener estilos con `getSampleStyleSheet()` (por ejemplo `styles['Title']` y `styles['Normal']`);
4. dar formato a las tablas con `TableStyle` (fondo de encabezado, color de texto, alineación, fuente, grilla);
5. generar el archivo con `doc.build(elementos)`.

Para incorporar un gráfico, el ejemplo lo crea con `matplotlib.pyplot`, lo guarda en memoria con `BytesIO` (`plt.savefig(buffer, format='png')` y `buffer.seek(0)`) y lo agrega con `Image(buffer, width=..., height=...)`.

Son formas observadas: no obligan a usar el tamaño `letter`, gráficos de torta, los colores del ejemplo ni a guardar el gráfico en memoria en lugar de un archivo temporal. El material menciona WeasyPrint, xhtml2pdf y FPDF como alternativas, sin desarrollarlas.

### 7.11 Ejercicios propuestos en la guía de patrones

La guía propone: costos de envío con Strategy (normal, express y económico sobre un paquete de 5 kg), máquina expendedora con State (`SinDinero`, `ConDinero`, `SinStock`) y curso con alumnos recorrido mediante Iterator, con un segundo iterador para notas mayores o iguales a 6. Al resolverlos, respetar las condiciones de cada enunciado; por ejemplo, en el ejercicio de Iterator el programa principal no debe recorrer directamente la lista interna del curso.

---

## 8. Límites del contenido actual

Herencia, polimorfismo, contratos abstractos, pytest, los seis patrones, SQLite y los reportes ya cuentan con material específico. Usarlos cuando corresponda, sin exigirlos retroactivamente en ejercicios anteriores.

Mantener estos límites:

* Las interfaces gráficas no están desarrolladas en el material de la cátedra. Una interfaz de métodos no habilita agregar una GUI. En el TP Integrador, la interfaz de presentación es una decisión del grupo registrada en la documentación del proyecto (sección 16.1); no se le atribuye aval académico.
* El acceso a datos abordado es SQLite con SQL directo. Las menciones a otros motores o cadenas de conexión en ejemplos no exigen instalarlos ni incorporar ORM o frameworks de persistencia.
* No asumir que cualquier patrón de diseño ya está abordado: el alcance incorporado es Singleton, Factory, Observer, State, Strategy e Iterator.
* Implementar varias interfaces no habilita por defecto jerarquías complejas de herencia múltiple concreta, mixins o resolución avanzada de métodos.
* Unittest, fixtures, mocks, cobertura y CI/CD solo se mencionan: no imponer técnicas, herramientas ni porcentajes de cobertura basándose en estos documentos.
* Las menciones a metaclases, concurrencia o thread-safety no obligan a implementarlas en los ejercicios de Singleton ni en las simulaciones de patrones.
* Generadores, `yield` e `itertools` no están desarrollados: no reemplazar con ellos un iterador explícito evaluado.
* Para reportes, el material desarrolla ReportLab, Matplotlib y `csv`. WeasyPrint, xhtml2pdf, FPDF y `pandas` solo se mencionan: no incorporarlos sin pedido explícito.

Si el enunciado requiere un contenido más avanzado, buscar su material específico o aclarar el supuesto. No completar vacíos con una arquitectura ajena al objetivo pedagógico.

---

## 9. Complejidad

Priorizar claridad, legibilidad, facilidad de explicación, correspondencia con el enunciado y simplicidad razonable.

Evitar sobreingeniería, abstracciones prematuras, arquitecturas preventivas, patrones innecesarios, optimizaciones sin necesidad y dependencias externas ajenas al objetivo pedagógico.

### 9.1 Complementos de buena práctica general

Las siguientes indicaciones complementan la implementación y verificación; **no se presentan como convenciones confirmadas de la cátedra**:

* Mantener la validación de dominio mediante condiciones y excepciones apropiadas. Las aserciones de tests no sustituyen esas validaciones.
* Capturar errores pertinentes sin ocultar fallos inesperados ni informar éxito después de una excepción.
* Cerrar solo los recursos que se hayan creado correctamente, incluso si falla la conexión o una operación SQL.
* Verificar modificaciones y eliminaciones en una base de prueba aislada, temporal o en memoria, nunca alterando datos reales para probar.
* Revisar el alcance de `WHERE` antes de modificar o eliminar filas. No inventar nombres de tablas, claves, restricciones ni datos de conexión.
* Evitar que tests, importaciones o simulaciones provoquen solicitudes interactivas, esperas prolongadas o cambios externos innecesarios.
* Al generar gráficos con Matplotlib sin pantalla (por ejemplo dentro de un servidor o en pruebas), usar un backend no interactivo como `Agg` y cerrar la figura con `plt.close()` después de guardarla, para no acumular figuras entre reportes.
* Generar los archivos de reportes en una ubicación configurada o temporal, sin sobrescribir archivos del usuario ni versionar los generados.
* Al escribir CSV con `csv.writer`, abrir el archivo con `newline=""` y una codificación explícita, según la documentación del módulo.

---

## 10. Verificación

Antes de finalizar:

1. Revisar el enunciado.
2. Ejecutar el programa cuando sea posible.
3. Probar casos normales, límites y errores aplicables.
4. Con archivos, verificar inexistencia, vacío, formato y efecto del modo cuando corresponda.
5. Con objetos, verificar referencias compartidas o independientes, invariantes y cardinalidad.
6. Con herencia, verificar inicialización de base y derivada, comportamiento heredado y redefiniciones.
7. Con polimorfismo e interfaces, verificar el mismo mensaje sobre distintas implementaciones y los contratos abstractos necesarios.
8. Con pruebas, ejecutar la suite pertinente y registrar el comando y resultado reales. Pueden usarse `pytest`, `pytest archivo.py`, `pytest -v` o `pytest -k "nombre"`, según el entorno y la selección necesaria.
9. Con Singleton, verificar identidad de la instancia y conservación de su estado entre accesos, sin contaminar otras pruebas.
10. Con Factory u Observer, verificar productos y contratos o suscripción y notificación, según corresponda.
11. Con State o Strategy, verificar delegación y transiciones válidas o resultados de cada algoritmo y su intercambio. En State, verificar también las operaciones no permitidas en cada estado y los estados finales.
12. Con Iterator, verificar el recorrido completo, la colección vacía, el fin mediante `StopIteration`, que dos recorridos sucesivos de la colección funcionen (iterador nuevo por recorrido) y, si existe, el criterio de los iteradores filtrados.
13. Con SQLite, verificar las operaciones ABMC pertinentes, consultas vacías, parámetros, restricciones y fallos; comprobar persistencia tras `commit()` y ausencia de cambios parciales tras `rollback()` cuando la actividad evalúe transacciones.
14. Con reportes, verificar los valores calculados contra datos conocidos, el caso sin datos y que el archivo generado se abra; comprobar que el reporte no modificó datos.
15. Confirmar que no se alteraron requisitos ajenos.
16. Revisar el diff final.

No afirmar que funciona si no pudo verificarse. Si faltan dependencias, no se descubrieron pruebas o no se pudo ejecutar una comprobación, informar exactamente esa limitación.

---

## 11. Informe final

Informar brevemente:

* archivos modificados;
* implementación realizada;
* criterio seguido;
* verificación ejecutada;
* supuestos;
* problemas pendientes.

No explicar línea por línea salvo solicitud.

---

## 12. Evolución de este archivo

El agente **no debe modificar este `AGENTS.md` por iniciativa propia**.

Si detecta una posible nueva convención, debe informarla como:

> Candidato a nueva convención de DAO.

Solo incorporarla cuando el usuario lo solicite. No convertir ejemplos aislados en reglas permanentes.

---

## 13. Clasificación de reglas

### CONFIRMADA

La cátedra establece explícitamente que una forma debe usarse, evitarse o preferirse.

### OBSERVADA

La práctica aparece en ejemplos oficiales, pero no se indica que sea obligatoria.

### BUENA PRÁCTICA GENERAL

Proviene de Python o ingeniería de software. Puede aplicarse si no contradice el enfoque académico, pero no presentarse como regla de la cátedra.

---

## 14. Regla fundamental

El objetivo no es producir el código más sofisticado, sino una solución:

**correcta + comprensible + justificable + acorde al nivel y criterios actuales de DAO.**

---

## 15. Material incorporado

### 15.1 Actualización del 9 de octubre de 2026

Se conservó el contenido previo hasta composición, agregación y cardinalidad y se amplió con estos documentos:

| Documento | Alcance utilizado |
| --- | --- |
| `semana-05.pdf` | Capítulo 10: herencia; capítulo 11: polimorfismo, clases abstractas e interfaces; capítulo 12: testing unitario y pytest. |
| `TESTING - Test Unitario en Python.pptx.pdf` | Pruebas unitarias, organización, aserciones, parametrización y ejecución de pytest. |
| `Patrones.pdf` | Concepto y descripción de patrones; Singleton, Factory y Observer. |
| `semana-09.pdf` | Capítulo 15: Singleton y variantes; capítulo 16: State, Strategy y alternativas funcionales. |
| `DB Guia Objetos de Acceso.docx` | Conexión, cursor, comandos SQL, parámetros, resultados, ABMC y transacciones. |
| `Material conceptual.pdf` | SQLite, ejecución y recuperación mediante cursores, operaciones SQL y manejo de errores y rollback. |

No convertir erratas o errores de extracción en convenciones: contrastar el original y verificar la API cuando haga falta. La grafía `executeScript()` se normaliza a `executescript()`, comprobada en el módulo `sqlite3` disponible.

### 15.2 Actualización del 30 de octubre de 2026

Actualización solicitada por el usuario. Se incorporan los PDF cargados en el proyecto:

| Documento | Alcance utilizado |
| --- | --- |
| `Guia_Patrones_Strategy_State_Iterator_Python.pdf` | Strategy (descuentos), State (pedido Pendiente → Enviado → Entregado), Iterator (biblioteca), comparación entre los tres y ejercicios propuestos. Secciones 3, 6.16, 6.20, 6.24, 7.5, 7.11 y 8. |
| `Reportes en Python.pdf` | ReportLab, tablas y estilos, gráficos con Matplotlib incorporados al PDF y módulo `csv`. Secciones 3, 6.4, 6.25, 7.10 y 8. |
| `tema3.pdf` | Consigna del TP Integrador 2026, Tema 3. Sección 16. |
| `semana-09 1.pdf` | Mismo contenido que `semana-09.pdf` (capítulos 15 y 16), ya incorporado en 15.1. Sin reglas nuevas. |
| `Patrones 1.pdf` | Mismo contenido que `Patrones.pdf` (Singleton, Factory y Observer), ya incorporado en 15.1. Sin reglas nuevas. |

Verificación realizada en esta actualización: se ejecutaron los ejemplos de ReportLab (tabla y gráfico con Matplotlib), State (pedido) e Iterator (biblioteca) de los PDF con ReportLab 5.0.1, Matplotlib 3.11.2 y Python 3; todos produjeron el resultado descripto en el material.

Erratas detectadas, que no deben convertirse en convenciones:

* `Pip install matplotlib.` se escribe `pip install matplotlib`.
* En el ejemplo del gráfico, el comentario «Cerrar el documento PDF» acompaña a `doc.build(elements)`: ese método genera y escribe el archivo; no es una operación de cierre separada.
* El segundo ejemplo crea `Paragraph` sin estilo. Funciona en la versión probada, pero el primer ejemplo pasa un estilo de `getSampleStyleSheet()`; preferir indicar el estilo por coherencia.
* En `tema3.pdf`, «Gesturar clientes frecuentes» corresponde a «Gestionar clientes frecuentes».

---

## 16. TP Integrador 2026 — Tema 3

### 16.1 Fuentes y autoridad

* `tema3.pdf` es el enunciado del TP: tiene la máxima prioridad para todo trabajo sobre él (sección 2, punto 1).
* Las decisiones del grupo están documentadas en el proyecto: `DECISIONES_F00.md`, `PLANIFICACION_TP_POO.md`, `PROPUESTA_ARQUITECTURA_REACT_PYTHON.md`, `DER.md`, `desiciones_estilos.md` y `LEVANTAR_PROYECTO.md`. Leer las pertinentes antes de proponer o implementar, y no reabrir decisiones aprobadas sin pedido del usuario.
* Las decisiones del grupo no son reglas de la cátedra. No atribuirles aval docente ni presentarlas como convenciones confirmadas.

### 16.2 Contexto

Un comercio minorista con varios locales se abastece desde un Centro de Distribución (CD). Cada local vende al público, controla su stock y solicita reposición al CD, que prepara bultos, los despacha y los locales los reciben. Nada debe ingresar a stock vendible sin verificación. El sistema integra compras, ventas, inventario y logística interna, mantiene actualizado el stock y permite conocer el resultado económico de las operaciones por período.

### 16.3 Obligaciones del enunciado

**Procesos obligatorios:**

1. Administrar sucursales/locales y Centro de Distribución.
2. Administrar productos, categorías, precios, niveles mínimos de existencia y proveedores.
3. Consolidar necesidades de los locales en una orden de reposición hacia el CD, indicando origen y destino.
4. Empaquetar mercadería en bultos/contenedores, asignando remito de despacho y precinto de seguridad.
5. Registrar el despacho de los bultos desde el CD.
6. Registrar la recepción en el local destino, verificando que el precinto no haya sido violado.
7. Registrar ventas con uno o más productos, cobros con medios de pago, emisión de comprobante y devoluciones con su impacto en stock y caja.

**Validaciones de negocio:**

1. El stock no impacta como Disponible en el local destino hasta que el remito y el contenedor pasen a Verificado. Si el precinto llega roto, pasa a Rechazado y no habilita venta (rechazo logístico).
2. Trazabilidad inmutable de los estados del bulto: Preparado, Precintado, En tránsito, Recibido, Verificado/Rechazado.
3. No vender cantidades superiores al stock disponible y verificado.
4. Evitar productos o proveedores duplicados según los identificadores definidos.
5. No aceptar devoluciones que no correspondan a una venta registrada o que incumplan las reglas establecidas.

**Mínimos académicos:**

* aplicar al menos **dos patrones de diseño**;
* implementar al menos **cuatro reportes no triviales**;
* cumplir todos los procesos obligatorios y las validaciones;
* el ciclo de vida del bulto/contenedor y sus estados se evalúa críticamente en el modelo;
* el grupo debe identificar entidades, atributos, relaciones y reglas adicionales para compras, logística y ventas.

### 16.4 Procesos opcionales y reportes sugeridos

Opcionales (implementar solo si el grupo lo decide): órdenes de compra sugeridas por faltantes; promociones, descuentos y listas de precios; lotes, números de serie o vencimientos; clientes frecuentes, cuentas corrientes o beneficios; inventarios físicos y conciliación de diferencias.

Reportes sugeridos: ventas e ingresos por período, local y medio de pago; productos más vendidos y margen estimado; existencias actuales y productos en stock mínimo; bultos rechazados o mermas por rotura de precinto; tiempo promedio de tránsito CD–locales y movimientos/valorización del inventario.

Los reportes sugeridos son títulos orientativos: el enunciado no obliga a implementar las cinco familias ni define «no trivial». Una interpretación razonable, a confirmar con el docente, es que el reporte combine datos de varias entidades, agrupe o calcule y admita filtros, por ejemplo por período o local; un listado directo de una tabla difícilmente califique.

### 16.5 Aplicación del material de la cátedra al TP

* **Patrones:** elegir los que resuelvan un problema real del dominio y justificarlos con la sección 6.16. Los patrones con material son los de la sección 8. El ciclo de vida del bulto es el caso que el enunciado destaca para evaluación; State es la decisión registrada por el grupo para ese ciclo. Consultar la documentación del proyecto antes de proponer un patrón adicional.
* **Historia inmutable:** el estado actual del bulto no sustituye la historia de transiciones. Con State, la transición la decide el estado/contexto (sección 6.20) y cada cambio deja un registro que no se edita ni se borra.
* **Composición y agregación:** decidir cada relación con las preguntas de la sección 6.11; una referencia o clave foránea no determina por sí sola el tipo de relación.
* **Persistencia:** SQLite con `sqlite3`, SQL parametrizado y transacciones que incluyan todos los efectos de una misma operación (secciones 6.21 a 6.23).
* **Reportes:** consultan operaciones confirmadas y no modifican stock ni caja. ReportLab, Matplotlib y `csv` son las herramientas presentadas por la cátedra; su adopción para los reportes del TP es una decisión del grupo y debe respetar las decisiones ya registradas (por ejemplo, el comprobante de venta se imprime desde el navegador, sin PDF).
* **Pruebas:** cubrir las cinco validaciones con pytest, incluido cada estado del bulto y los intentos de venta antes de la verificación.

### 16.6 Invariantes que ninguna implementación puede romper

* Verificar solo el bulto o solo el remito nunca habilita stock en el destino.
* Un precinto roto deja el bulto Rechazado y su mercadería no vendible.
* Ningún estado registrado del bulto se edita ni se elimina.
* Una venta inválida no deja efectos parciales en stock, caja ni comprobante.
* Las validaciones definitivas se ejecutan en el backend Python; una validación del cliente no es autoridad.
