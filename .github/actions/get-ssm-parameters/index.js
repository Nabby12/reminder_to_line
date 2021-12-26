'use strict'

const core = require('@actions/core')

const DEFAULT_REGION = core.getInput('default_region')
const LAMBDA_NAME = core.getInput('lambda_name')
const ENV_NAME = core.getInput('env_name')
const CD_PARAMETERS = core.getInput('cd_parameters').split('\n')
const PARAMETERS = core.getInput('parameters').split('\n')

const SSM_VERSION = '2014-11-06'
const AWS = require('aws-sdk')
AWS.config.update({
  region: DEFAULT_REGION,
  apiVersions: {
    ssm: SSM_VERSION
  }
})

const ssm = new AWS.SSM()

if (require.main === module) {
  handler()
}

async function handler() {
  try {
    const ssm_cd_path = '/cd/'
    const ssm_path = `/${LAMBDA_NAME}/${ENV_NAME}/`

    // 取得するパラメータストアのパス+名称を一つの配列に格納
    let ssm_params = []
    CD_PARAMETERS.map(parameter => {
      const param = {
        path: ssm_cd_path, 
        key: parameter
      }
      ssm_params.push(param)
    })
    PARAMETERS.map(parameter => {
      const param = {
        path: ssm_path, 
        key: parameter
      }
      ssm_params.push(param)
    })

    // 対象のパラメータストアの値をすべて取得
    let ssm_parameters = {}
    await Promise.all (
      ssm_params.map(async parameter => {
        const params = {
          Name: parameter.path + parameter.key,
          WithDecryption: true
        }
        const response = await ssm.getParameter(params)
        .promise()
        .then(data => {
          ssm_parameters[parameter.key] = data.Parameter.Value
          return 'get ssm parameter succeeded.'
        })
        .catch(err => {
          console.log(err)
          throw new Error('get ssm parameter failed.')
        })

        console.log(response)
      })
    )

    // outputに定義する値をマスク
    core.setSecret(JSON.stringify(ssm_parameters))
    // outputに取得した値を定義
    core.setOutput('ssm_parameters', JSON.stringify(ssm_parameters))
  } catch (error) {
    core.setFailed(error.message)
  }
}
