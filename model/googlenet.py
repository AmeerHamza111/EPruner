import torch
import torch.nn as nn

class Inception(nn.Module):
    def __init__(self, in_planes, n1x1, n3x3red, n3x3, n5x5red, n5x5, pool_planes, sketch_rate, tmp_name):
        super(Inception, self).__init__()
        self.sketch_rate = sketch_rate
        self.tmp_name=tmp_name

        self.n1x1 = n1x1
        self.n3x3 = n3x3
        self.n5x5 = n5x5
        self.pool_planes = pool_planes

        # 1x1 conv branch
        if self.n1x1:
            conv1x1 = nn.Conv2d(in_planes, n1x1, kernel_size=1)
            conv1x1.tmp_name = self.tmp_name

            self.branch1x1 = nn.Sequential(
                conv1x1,
                nn.BatchNorm2d(n1x1),
                nn.ReLU(True),
            )

        # 1x1 conv -> 3x3 conv branch
        if self.n3x3:
            conv3x3_1=nn.Conv2d(in_planes, int(n3x3red * self.sketch_rate), kernel_size=1)
            conv3x3_2=nn.Conv2d(int(n3x3red * self.sketch_rate), n3x3, kernel_size=3, padding=1)
            conv3x3_1.tmp_name = self.tmp_name
            conv3x3_2.tmp_name = self.tmp_name

            self.branch3x3 = nn.Sequential(
                conv3x3_1,
                nn.BatchNorm2d(int(n3x3red * self.sketch_rate)),
                nn.ReLU(True),
                conv3x3_2,
                nn.BatchNorm2d(n3x3),
                nn.ReLU(True),
            )

        # 1x1 conv -> 5x5 conv branch
        if self.n5x5 > 0:
            conv5x5_1 = nn.Conv2d(in_planes, int(n5x5red * self.sketch_rate), kernel_size=1)
            conv5x5_2 = nn.Conv2d(int(n5x5red * self.sketch_rate), int(n5x5 * self.sketch_rate), kernel_size=3, padding=1)
            conv5x5_3 = nn.Conv2d(int(n5x5 * self.sketch_rate), n5x5, kernel_size=3, padding=1)
            conv5x5_1.tmp_name = self.tmp_name
            conv5x5_2.tmp_name = self.tmp_name
            conv5x5_3.tmp_name = self.tmp_name

            self.branch5x5 = nn.Sequential(
                conv5x5_1,
                nn.BatchNorm2d(int(n5x5red * self.sketch_rate)),
                nn.ReLU(True),
                conv5x5_2,
                nn.BatchNorm2d(int(n5x5 * self.sketch_rate)),
                nn.ReLU(True),
                conv5x5_3,
                nn.BatchNorm2d(n5x5),
                nn.ReLU(True),
            )

        # 3x3 pool -> 1x1 conv branch
        if self.pool_planes > 0:
            conv_pool = nn.Conv2d(in_planes, pool_planes, kernel_size=1)
            conv_pool.tmp_name = self.tmp_name

            self.branch_pool = nn.Sequential(
                nn.MaxPool2d(3, stride=1, padding=1),
                conv_pool,
                nn.BatchNorm2d(pool_planes),
                nn.ReLU(True),
            )

    def forward(self, x):
        out = []
        y1 = self.branch1x1(x)
        out.append(y1)

        y2 = self.branch3x3(x)
        out.append(y2)

        y3 = self.branch5x5(x)
        out.append(y3)

        y4 = self.branch_pool(x)
        out.append(y4)
        return torch.cat(out, 1)


class GoogLeNet(nn.Module):
    def __init__(self, block=Inception, filters=None, sketch_rate=None):
        super(GoogLeNet, self).__init__()

        if sketch_rate is None:
            self.sketch_rate = [1] * 9
        else:
            self.sketch_rate = sketch_rate

        conv_pre = nn.Conv2d(3, 192, kernel_size=3, padding=1)
        conv_pre.tmp_name='pre_layer'
        self.pre_layers = nn.Sequential(
            conv_pre,
            nn.BatchNorm2d(192),
            nn.ReLU(True),
        )
        if filters is None:
            filters = [
                [64, 128, 32, 32],
                [128, 192, 96, 64],
                [192, 208, 48, 64],
                [160, 224, 64, 64],
                [128, 256, 64, 64],
                [112, 288, 64, 64],
                [256, 320, 128, 128],
                [256, 320, 128, 128],
                [384, 384, 128, 128]
            ]

        self.filters=filters

        self.inception_a3 = block(192, filters[0][0],  96, filters[0][1], 16, filters[0][2], filters[0][3], self.sketch_rate[0], 'a3')
        self.inception_b3 = block(sum(filters[0]), filters[1][0], 128, filters[1][1], 32, filters[1][2], filters[1][3], self.sketch_rate[1], 'a4')

        self.maxpool1 = nn.MaxPool2d(3, stride=2, padding=1)
        self.maxpool2 = nn.MaxPool2d(3, stride=2, padding=1)

        self.inception_a4 = block(sum(filters[1]), filters[2][0],  96, filters[2][1], 16, filters[2][2], filters[2][3], self.sketch_rate[2], 'a4')
        self.inception_b4 = block(sum(filters[2]), filters[3][0], 112, filters[3][1], 24, filters[3][2], filters[3][3], self.sketch_rate[3], 'b4')
        self.inception_c4 = block(sum(filters[3]), filters[4][0], 128, filters[4][1], 24, filters[4][2], filters[4][3], self.sketch_rate[4], 'c4')
        self.inception_d4 = block(sum(filters[4]), filters[5][0], 144, filters[5][1], 32, filters[5][2], filters[5][3], self.sketch_rate[5], 'd4')
        self.inception_e4 = block(sum(filters[5]), filters[6][0], 160, filters[6][1], 32, filters[6][2], filters[6][3], self.sketch_rate[6], 'e4')

        self.inception_a5 = block(sum(filters[6]), filters[7][0], 160, filters[7][1], 32, filters[7][2], filters[7][3], self.sketch_rate[7], 'a5')
        self.inception_b5 = block(sum(filters[7]), filters[8][0], 192, filters[8][1], 48, filters[8][2], filters[8][3], self.sketch_rate[8], 'b5')

        self.avgpool = nn.AvgPool2d(8, stride=1)
        self.linear = nn.Linear(sum(filters[-1]), 10)

    def forward(self, x):

        out = self.pre_layers(x)
        # 192 x 32 x 32
        out = self.inception_a3(out)

        # 256 x 32 x 32
        out = self.inception_b3(out)
        # 480 x 32 x 32
        out = self.maxpool1(out)

        # 480 x 16 x 16
        out = self.inception_a4(out)

        # 512 x 16 x 16
        out = self.inception_b4(out)

        # 512 x 16 x 16
        out = self.inception_c4(out)

        # 512 x 16 x 16
        out = self.inception_d4(out)

        # 528 x 16 x 16
        out = self.inception_e4(out)
        # 823 x 16 x 16
        out = self.maxpool2(out)

        # 823 x 8 x 8
        out = self.inception_a5(out)

        # 823 x 8 x 8
        out = self.inception_b5(out)

        # 1024 x 8 x 8
        out = self.avgpool(out)
        out = out.view(out.size(0), -1)
        out = self.linear(out)

        return out

def googlenet(sketch_rate=None):
    return GoogLeNet(block=Inception, sketch_rate=sketch_rate)