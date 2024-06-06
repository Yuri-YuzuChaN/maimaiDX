class UserNotFoundError(Exception):
    
    def __str__(self) -> str:
        return '''未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。
如未绑定，请前往查分器官网进行绑定
https://www.diving-fish.com/maimaidx/prober/'''


class UserDisabledQueryError(Exception):
    
    def __str__(self) -> str:
        return '该用户禁止了其他人获取数据。'
    

class ServerError(Exception):
    
    def __str__(self) -> str:
        return '别名服务器错误，请联系插件开发者'


class EnterError(Exception):
    
    def __str__(self) -> str:
        return '参数输入错误'


class CoverError(Exception):
    """图片错误"""


class UnknownError(Exception):
    """未知错误"""