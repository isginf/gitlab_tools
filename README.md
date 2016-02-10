# gitlab_tools

A collection of tools we use to manage our Gitlab CE service at the departement of informatics at the ETH Zurich.

- backup_config.py contains needed configuration like Gitlab URL and token
- backup-gitlab-projects.py is a tool to backup individual projects using the Gitlab REST API
- gitlab_lib.py is the central library used by the tools
- gitlab-project-search.py let you search for projects by id, name or description and dumps their meta information
- restore-gitlab-project.py can restore a whole project or just a single component like all issues


## Requirements

- You need to install the Python module requests either by using `pip install -r requirements.txt` or using the package manager of your OS

Please make sure to edit backup_config.py to fit your needs.


## Usage

### Search for a project

gitlab-project-search.py -p <search_string> [-d]

### Backup all projects

`backup-gitlab-projects.py-r /path/to/repositories/ -o /my/backup/dir`

### Restore a single component of a project

`restore-gitlab-project.py -b /my/backup/dir/<project> -p <project_name_or_id> -c milestones`

### Restore a whole project

- Create the project in Gitlab
- Make sure all components used are enabled
- Members are not restored yet

`tar xvf /my/backup/dir/<project>/<project>.git.tgz
tar xvf /my/backup/dir/<project>/<project>.wiki.git.tgz
tar xvf /my/backup/dir/<project>/upload_<project>.tgz
chown -R git:git *

restore-gitlab-project.py -b /my/backup/dir/<project> -p <target_project_name_or_id>`


## Known issues

- By now the project to be restored and it's settings must be created by hand
- Members are not restored yet
- Repository, wiki and upload archives must be extracted manually


## License

Copyright 2016 ETH Zurich, ISGINF, Bastian Ballmann
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
