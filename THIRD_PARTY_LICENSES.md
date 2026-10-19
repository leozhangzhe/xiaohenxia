# 第三方来源与许可清单

日期：2026-10-19。原作者版权保留。本文件不替代完整许可证。

| 部分 | 版本 / 来源 | 许可和归档 |
| --- | --- | --- |
| SpiderFoot | https://github.com/smicallef/spiderfoot | MIT；根 LICENSE、模块作者头、THANKYOU |
| React、React DOM、Framer Motion、Lucide 等前端依赖 | frontend/package-lock.json | 各自许可全文：spiderfoot/static/react-auth/THIRD_PARTY_LICENSES.txt |
| Liquid Metal Shader | https://github.com/johnmamanao/nacre-ui | MIT；spiderfoot/static/vendor/liquid-metal/LICENSE、source-identity.json；third_party/liquid-metal 原组件及来源 |
| Liquid Glass 按钮 | 用户提供样本，frontend/components/ui/liquid-glass-button.tsx | 组件原样本保留；相关 React/Radix 许可见前端依赖归档 |
| jQuery | 3.7.1，https://github.com/jquery/jquery | MIT；third_party/runtime-assets/licenses/jquery |
| Bootstrap | 3.4.1，https://github.com/twbs/bootstrap | MIT；third_party/runtime-assets/licenses/bootstrap |
| AlertifyJS | 1.14.0，https://github.com/MohammadYounes/AlertifyJS | MIT；third_party/runtime-assets/licenses/alertifyjs |
| D3 | 3.5.17，https://github.com/d3/d3 | BSD-3-Clause；third_party/runtime-assets/licenses/d3 |
| Sigma | 1.2.2，https://github.com/jacomyal/sigma.js | MIT；third_party/runtime-assets/licenses/sigma |
| tablesorter | 2.32.0，https://github.com/Mottie/tablesorter/tree/v2.32.0 | MIT OR GPL-2.0，发布文件选 MIT；licenses/tablesorter/LICENSE 保留版权与全文 |
| Python 应用全部已安装依赖 | requirements-release-win-py312.lock.txt | third_party/python/inventory.json 记录每项版本、元数据许可及可用全文路径；licenses/ 保留随包文本 |
| Sherlock | 0.16.2，https://github.com/sherlock-project/sherlock | MIT；独立安装，环境及结果不打包 |
| Maigret | 0.6.6，https://github.com/soxoj/maigret | MIT；独立安装，环境及结果不打包 |
| Holehe | 1.61，https://github.com/megadose/holehe | GPL-3.0；独立调用，本包不分发工具环境；若再分发必须履行对应源码及许可义务 |
| WhatsMyName | ec273f81aa1b8728a932589dcba71c6894001acc，https://github.com/WebBreacher/WhatsMyName | CC BY-SA 4.0；规则安装时校验下载，保留归属和许可，不收入源码 ZIP |
| HIBP | https://haveibeenpwned.com/API/v3 | API 服务条款与归属；没有 Key 或泄露正文 |
| MySQL Community | 8.0.46，https://dev.mysql.com/downloads/mysql/8.0.html | GPL-2.0 及附加许可；二进制不在源码包，用户官方获取；third_party/mysql-artifact.json 记录 SHA-256 |
| CPython | 3.12.10，https://www.python.org/ | PSF 及第三方许可；解释器不在包中 |

外部工具依赖锁文件为 scripts/live-source-locks/*.txt，安装元数据与许可在对应独立环境保留。若日后整体分发工具/解释器/MySQL 环境，需要另外履行完整许可及适用源码义务。

前端直接依赖的实际版本和原许可另见 third_party/frontend/inventory.json 及同目录各包 LICENSE；构建内使用的传递依赖许可见 react-auth/THIRD_PARTY_LICENSES.txt。两份清单共同保留源码样本与正式构建的归属。

不使用 Poliigon、外部 HDRI、专有模型、公司品牌素材或 CDN。液态金属使用程序化 GLSL。旧字典、图片和模块保留原声明。leak-check 移植来源保留在 spiderfoot/leakcheck.py；样例数据已全部合成化。
