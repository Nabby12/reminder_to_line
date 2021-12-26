# reminder_to_line

## 導入

### 1. リポジトリをクローン

```bash
git clone git@github.com:toletta/reminder_to_line.git
```

### 2. 必要ファイル準備

- 下記のサンプルに沿って"env.json"を作成（ローカル実行の際に環境変数等の設定で必要）
- "yourFunction"は"template.yaml"で設定している関数名と同一
- "enironment1"等は"template.yaml"内"Parameters"以下で設定している変数名と同一

```json
{
 "yourFunction": {
   "environment1": "value1",
   "environment2": "value2"
 } 
}
```

### 3. ビルド

```bash
sam build
```

- AWS SAM CLI 必須
    - 参考： [AWS SAM CLI のインストール - AWS Serverless Application Model](https://docs.aws.amazon.com/ja_jp/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

### 4. ローカル実行

```bash
sam local invoke -n env.json
```

- "-n"オプションで環境変数を渡してローカル実行
- "-e"オプションで指定のeventをlambda_handler関数に渡してローカル実行

## デプロイローカル実行

### 1. 初回

```bash
sam deploy --config-env dev -g / sam deploy --config-env prd -g
```

- "--config-env [環境名]"で環境ごとにデプロイ
  - 開発用 / 本番用など、別lambdaとしてデプロイ可能
- "-g"で各種オプションを設定してデプロイ
  - 設定は"samconfig.toml"（初期値）でファイル生成され、保存される
    - 環境変数が記載されているため、env.jsonなどはgithubにあげない（.gitignoreに記載済み）

### 2. 2回目以降

```bash
sam deploy --config-env dev / sam deploy --config-env prd
```

- "samconfig.toml"で設定されている該当の環境名の値を使用してデプロイ実行

## デプロイ自動実行

- プルリクがマージされるとGithubActionsによりデプロイが実行される
- samconfig.tomlで指定していた環境変数等は、githubリポジトリのSecrets, SSM Parameterで設定する
  - 別途、.github/workflow/~.yml にて設定が必要
    - ~.ymlファイルは環境別に作成する
  - 複数環境を設定している場合、環境別にSecrets等を設定する
