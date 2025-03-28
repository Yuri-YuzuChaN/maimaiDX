from textwrap import dedent


class UserNotFoundError(Exception):
    
    def __str__(self) -> str:
        return dedent('''
            未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。
            如未绑定，请前往查分器官网进行绑定
            https://www.diving-fish.com/maimaidx/prober/
        ''').strip()


class UserNotExistsError(Exception):

    def __str__(self) -> str:
        return '查询的用户不存在'


class UserDisabledQueryError(Exception):

    def __str__(self) -> str:
        return '该用户禁止了其他人获取数据或未同意用户协议。'


class TokenError(Exception):

    def __str__(self) -> str:
        return '开发者Token有误'


class TokenDisableError(Exception):

    def __str__(self) -> str:
        return '开发者Token被禁用'


class TokenNotFoundError(Exception):

    def __str__(self) -> str:
        return '请先联系水鱼申请开发者token'


class MusicNotPlayError(Exception):
    
    def __str__(self) -> str:
        return '您未游玩该曲目'


class ServerError(Exception):

    def __str__(self) -> str:
        return '别名服务器错误，请联系插件开发者'


class EnterError(Exception):

    def __str__(self) -> str:
        return '参数输入错误'


class AliasesNotFoundError(Exception):
    
    def __str__(self) -> str:
        return '未找到别名'


class UnknownError(Exception):
    """未知错误"""