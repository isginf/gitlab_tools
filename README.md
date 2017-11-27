# gitlab_tools

A collection of tools we use to manage our Gitlab CE service at the departement of informatics at the ETH Zurich.

- gitlab_config.py contains needed configuration like Gitlab URL and token
- backup-gitlab-projects.py is a tool to backup individual projects using the Gitlab REST API
- gitlab_lib.py is the central library used by the tools
- gitlab-meta-util.py - Swiss army knife for Gitlab Metadata
- quota_hook.rb implements a nagging and max quota for git repositories (see below for installation instructions)
- restore-gitlab-project.py can restore a whole project or just a single component like all issues


## Requirements

- You need to install the Python module requests either by using `pip install -r requirements.txt` or using the package manager of your OS

Please make sure to edit gitlab_config.py to fit your needs.

To create a CLONE_ACCESS_TOKEN use the following procedure:

- Go to personal users settings -> Access token and generate a token (at least for CE it doesnt get saved in the database so we do it manually)
- su - git -c "PGHOST=/var/opt/gitlab/postgresql /opt/gitlab/embedded/bin/psql -U gitlab -d gitlabhq_production"
- insert into oauth_access_tokens (resource_owner_id, token, refresh_token, created_at, scopes) values (1, '$TOKEN', '$TOKEN', now(), 'api'); 


## Usage

### Search for a project

gitlab-meta-util.py -o projects -i <search_string>

### Get all ids of all projects in group mygroup and print their members

for PROJECT in $(gitlab-meta-util.py -o groups -i mygroup -p projects -P id); do echo -en "$PROJECT "; gitlab-meta-util.py -o projects -i $PROJECT -p members; done

### Set new projects_limit for a list of users

for USER in $(cat userlist.txt); do ./gitlab-meta-util.py -o users -i $USER -p projects_limit -V 23; done

### Backup all projects

`backup-gitlab-projects.py-r /path/to/repositories/ -o /my/backup/dir`

### Backup metadata and all projects of a single user

`backup-gitlab-projects.py-r /path/to/repositories/ -o /my/backup/dir -U <username>`

### Restore a single component of a project (component must be empty!)

`restore-gitlab-project.py -b /my/backup/dir/<project> -p <project_name_or_id> -c milestones`

### Restore a whole project

`restore-gitlab-project.py -b /my/backup/dir/<project> -p <target_project_name> -r <path_to_repositories_plus_namespace>`


## Quota hook installation

- Copy quota_hook.rb to /opt/gitlab/embedded/service/gitlab-shell/lib/quota_hook.rb
- Edit /opt/gitlab/embedded/service/gitlab-shell/hooks/pre-receive
- Add a line to require the module

```
require_relative '../lib/gitlab_access'
require_relative '../lib/quota_hook'
```

- And a line to execute the hook

```
if GitlabAccess.new(repo_path, key_id, refs, protocol).exec &&
    QuotaHook.new.pre_receive(repo_path, key_id, refs) &&
```

## License

Copyright 2017 ETH Zurich, ISGINF, Bastian Ballmann
E-Mail: bastian.ballmann@inf.ethz.ch
Web: http://www.isg.inf.ethz.ch

This is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

It is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License.
If not, see <http://www.gnu.org/licenses/>.
