# 道财榜·模拟数据演示版

这是道财榜V2.0的静态网站原型。

## 本地数据构建

```powershell
python .\build_data.py
```

脚本读取工作区根目录下的`data/*.csv`，生成`dist/data.json`。

## 本地预览

```powershell
python -m http.server 4173 --directory dist
```

所有企业和数据均为模拟内容，不对应任何真实企业。
