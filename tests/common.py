from bazoola import *


class TableA(Table):
    name = "a"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(5)),
        ]
    )


class TableB(Table):
    name = "b"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(5)),
            Field("a_id", FK("a")),
        ]
    )


class TableB_NullableFK(Table):
    name = "b2"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(5)),
            Field("a_id", FK("a", null=True)),
        ]
    )


class TableC(Table):
    name = "c"
    schema = Schema(
        [
            Field("id", PK()),
            Field("varchar", CHAR(5)),
            Field("int", INT()),
        ]
    )


class TableD(Table):
    name = "d"
    schema = Schema(
        [
            Field("id", PK()),
            Field("varchar", CHAR(5, null=True)),
            Field("int", INT(null=True)),
        ]
    )


class TableE(Table):
    name = "e"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", CHAR(20)),
        ]
    )


class TableF(Table):
    name = "f"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", TEXT()),
        ]
    )


class TableF_NullableText(Table):
    name = "f2"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text", TEXT(null=True)),
        ]
    )


class TableG(Table):
    name = "g"
    schema = Schema(
        [
            Field("id", PK()),
            Field("text1", TEXT()),
            Field("text2", TEXT(null=True)),
            Field("text3", TEXT()),
        ]
    )
