import random
def uotp():
    u_c=[chr(i) for i in range(ord('A'),ord('Z')+1)]
    l_c=[chr(i) for i in range(ord('a'),ord('z')+1)]
    uotp=''
    for i in range(2):
        uotp+=random.choice(u_c)
        uotp+=str(random.randint(0,9))
        uotp+=random.choice(l_c)
    return uotp