import handle
if __name__ == '__main__':
    '''
    这里的passenger经过了学生认证，需要加上(学生)在最后面,
    运行前请检查handle.py中的126和138行是否取消了注释，取消了注释将会直接确认下单！！！
    时间格式按照给出的样例书写
    '''
    user = handle.Qiangpiao("上海","北京","2025-02-04","G2","xxx(学生)")
    user.run()