# Recruiting Project

## プロジェクト概要

採用スクリーニング支援AIエージェントのプロジェクトです。候補者のCVと募集要項を比較し、スクリーニング結果をレポートとして出力します。

## フォルダ構成

```
recruiting_project/
├── input/                  # 候補者CVファイルを格納（PDFのみ処理対象）
├── job-descriptions/       # 募集職種ごとの募集要項（*_job-description.md）
├── output/                 # スクリーニング結果レポートの出力先（CV1件につき1ファイル）
├── error/                  # 非PDFファイルの隔離先
├── json/                   # 前処理・マッピング結果の中間JSONファイル
├── src/                    # 前処理Pythonスクリプト群
│   ├── preprocess.py       # PDF抽出・非PDF仕分け
│   ├── load_context.py     # 募集要項・テンプレート読み込み
│   └── map_context.py      # 募集要項の構造化マッピング
├── templates/              # レポートテンプレートと評価基準
│   ├── screening-report-template.md    # レポートの体裁・章立て基準
│   ├── evaluation-rubric.md            # A〜D評価の定義・判定基準
│   └── job-description-template.json  # 募集要項の構造化スキーマ
└── .claude/commands/       # カスタムスキル定義
    └── cv-screening.md     # /cv-screening スキル定義
```

## カスタムスキル

### `/cv-screening`

候補者CVを全募集職種の要件と照合し、スクリーニングレポートを `output/` に生成します。

**使い方:**
1. `input/` フォルダにCVファイル（PDF）を配置する
2. `/cv-screening` を実行する
3. 表示された候補者数・評価職種一覧を確認し `yes` / `no` で実行可否を回答する
4. `output/` に生成されたレポートを確認する

## 規約

- CVファイルは `input/` フォルダに配置する（処理対象はPDFのみ）
- Word / Google Docs 等の非PDFファイルは自動的に `error/` フォルダへ移動される
- 募集要項は `job-descriptions/` フォルダに `*_job-description.md` の命名規則で保存する
- 評価は全募集職種を対象に一括実行。ユーザーは実行可否のみ回答する
- 出力レポートは候補者1名につき1ファイル。複数CVの結果を1ファイルに混在させない
- レポート内に全職種の詳細評価と全体サマリーを含める
- 出力ファイル名は5桁のランダム数字（例: `38271_screening-report.md`）。候補者名をファイル名に含めない

## 評価基準（概要）

詳細は `templates/evaluation-rubric.md` を参照。

| 評価 | ラベル | 判定基準 |
|------|--------|---------|
| A | 強く推薦 | 必須要件の全項目平均3.5以上、スコア1が1件以内、スコア2が1件以内 |
| B | 推薦 | 必須要件の全項目平均3.0超、スコア1が1件以内、スコア2が3件以内（Aの基準は満たさない） |
| C | 条件付き推薦 | 必須要件の全項目平均2.5以上（A・B基準を満たさない） |
| D | 見送り推奨 | 必須要件の全項目平均2.5未満 |
