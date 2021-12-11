from PIL import Image
from numpy import *
import numpy
from skimage import io
from bitarray import bitarray
from Crypto.Cipher import AES
from Crypto import Random
import base64
import random
import os.path
import sys

base_path = os.path.dirname(os.path.realpath(__file__))  # 获取当前路径
filename = os.path.join(os.path.dirname(base_path), 'receiver_image',sys.argv[2]+'_embedImage.png')
E = io.imread(filename) #加密后的图片矩阵
kuan,gao = E.shape #得到宽高像素

K = int(kuan*gao/64) #将图像分割为K块
heng = int(kuan/8) #横着的块数
shu = int(gao/8) #竖着的快数

def getci(i): #获取第i块的全部信息
    ci = [] #第i个块的信息 512bit 有8个元素，每个元素有64bit
    for k in range(8):
        cik = bitarray() #第k个bit平面 64bit
        for r in range(8):#第（r,s）个像素
            for s in range(8):
                cirsk = (E[(i%heng)*8+r,int(i/shu)*8+s]>>k)%2
                cik.append(cirsk)
        ci.append(cik)
    return ci

e = [] #全部图像的信息512K bit 8K个元素，每个元素有64bit

for i in range(K):
    e += getci(i) #8K个元素，每个元素有64bit

c = e[::8] #提取的K块的最低位平面信息，K个元素，每个元素64bit
# print(len(c)) #4096=K
# print(len(c[0])) #64bit

embedkey = sys.argv[1]
permutationseed = int(embedkey[0:8],16)
#伪随机置换矩阵
# permutationseed = 42
fp = numpy.random.RandomState(permutationseed).permutation(K)
f = list(fp)  #f为伪随机置换
rvf =  [0 for i in range(K)] #rvf为f的逆置换，之后复原有用
for i in range(K):
    rvf[f[i]] = i
    
cf = [] #c的置换，K个元素，每个元素64bit
for i in range(K):
    cf.append(c[f[i]])
# print(len(cf))#4096=K
# print(len(cf[0]))#64

u = 2 #预定义参数 暂时设置为2
L = int(K/u) #将cf分成L组 
w = 1   

#对于第l组
def extract1(l,cf,w): 
    gl = bitarray() #将cf分成L组后，gl为第l组的信息，有64ubit
    for i in range(u):
        gl += cf[l*u+i]
    #print(len(gl))  #128
    al = gl[0:w]
    return al
 
a = bitarray()
for l in range(L):
   a += extract1(l,cf,w)
 
# print(a)
#生成L*w个bit密码mima
jiamiseed = int(embedkey[8:16],16)
# jiamiseed = 123356789
mimaint = numpy.random.RandomState(jiamiseed).randint(0,2,L*w)
mima = bitarray()
for i in range(L*w):
    mima = mima + str(mimaint[i])

#a为加密好的信息，准备提取
m = mima^a #a为L*w bit，加密以后

'''
def bitarray2str(bitarray_obj):
    return bitarray_obj.tostring()
'''

def bitarray2str(bit):
    return bit.tobytes().decode('utf-8')

print(bitarray2str(m))


