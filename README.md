# Core infrastructure to serve multiple TG bots

## Overview

An API server with backend redis database which:
* Stores messages from multiple bots
* Allows clients to get stored messages
* Filter results by bot, state

```sh
Bot 1 ---> \
Bot 2 ---> API Server (EC2) ---> Redis (ElastiCache)
Bot 3 ---> /     ^
                 |
            Website (S3)
```

### API server

The api-server provides public endpoints for storing and fetching telegram messages.
So far, the only requirement is for payloads to be sent as json with the following schema.

```json
{
    "bot_id": "name of your bot",
    "message": {
        "state": "bot state (you define it)",
        "text": "the message text",
        "timestamp": "%Y-%m-%d_%H:%M:%S"
    }
}
```

### Bot platform

The infrastructure is designed to serve multiple bots created by different people from everywhere.
Developers will own their own source code in their own repo, and we just give you the resources to keep it running.
To begin, create your repo from this template [test-bot](https://github.com/tee-gee-bots/test-bot) and follow the onboarding instructions in the README.md.

### Deployment

The exciting part of this design is its automated deployment to AWS. Deployment details are fully managed by terraform infrastructure-as-code: resources, roles, security policies, networking. Continuous deployment is enabled by Github Actions. Onboarded bots make use of a reusable workflow that lets developers focus on designing bot functionality rather than stress over deployment and integration issues. We currently support `sandbox` deployment but can switch to `production` mode when ready.

## How to onboard a new bot

1. Get the following information from developer:
    * BOT_GITHUB_ORG_NAME
    * BOT_NAME (must be unique)
2. Add these into `shared/terraform/main.tf`
```hcl
module "bot_platform" {
    ...
    bot_configs = {
        "test-bot" = {
        github_org = "tee-gee-bots"
        }
        # "BOT_NAME" = {
        #   github_org = "BOT_GITHUB_ORG_NAME"
        # }
    }
}
```
3. Commit the change to deploy the new infrastructure

## Todo

Idea dump:
* Onboard multiple bots
    * Bot 1: Produce input messages on demand (e.g. Present real-user members with `Would you like to... Y/N` question)
    * Bot 2: Monitor real-user replies to input message (e.g. Grant the wish if `Y` and present link to updated website)
* Improve onboarding checklist for both bot developer and infrastructure admin
* Integrate with front-end website
    * A simple website that polls api-server for updated information
    * Displays content based on updated information (text or image from an image bank)
* Improve/swap front-end for better, more creative experience
    * Doesn't have to be website - twitter bot?
* Improve server design
    * Rate limit requests from clients (bots and website)
    * CORS for website
    * Data retention
    * Reduce infrastructure cost
    * Scalable in the right ways?
    * Sandbox vs Prodction