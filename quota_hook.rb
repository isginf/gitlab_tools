#
# Enforce soft and hard quota for gitlab repositories
#
# Copyright 2016 ETH Zurich, ISGINF, Bastian Ballmann
# Email: bastian.ballmann@inf.ethz.ch
# Web: http://www.isg.inf.ethz.ch
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License.
# If not, see <http://www.gnu.org/licenses/>.

class QuotaHook
  class QuotaExceededError < StandardError; end

  def initialize()
    @nag_quota = 950 # size in mb
    @max_quota = 1024 # size in mb
  end

  #
  # pre_receive hook to check quota
  #
  def pre_receive(repo_path, key_id, refstr)
    refs = refstr.split(" ")

    if is_not_ref(refs[0])
      raise TypeError, ref[0] + " is not a valid ref"
    elsif is_not_ref(refs[1])
      raise TypeError, ref[1] + " is not a valid ref"
    end

    if is_new_branch(refs[0])
      return true
    end                      
    
    old_repo_size = repo_size(repo_path)
    changed_objects = get_changed_objects(repo_path, refs[0], refs[1])

    if not only_deletes(changed_objects)
      size_of_changes = changed_objects_size(changed_objects, repo_path)
      new_repo_size = old_repo_size + size_of_changes

      if new_repo_size >= @max_quota
        msg = "Your commit exceeded your quota size of %d mb. Please use LFS for big files!" % [@max_quota]
        raise QuotaExceededError, msg

      elsif new_repo_size >= @nag_quota
        msg_text = <<MSG_END

*** YOU ARE OVER NAGGING QUOTA! ***

Repo size: #{new_repo_size} mb
(Nagging quota is #{@nag_quota} mb / Max quota #{@max_quota} mb)

*** YOU ARE OVER NAGGING QUOTA! ***

MSG_END

        print msg_text
      end
    end

    return true
  end


  #
  # get a list of changed objects and their properties
  # :100644 000000 5713ac70b1aba88fc2d218a015d0b7ff7bf5c244 0000000000000000000000000000000000000000 D      .gitattributes
  # returns array of hashes
  #
  def get_changed_objects(repo_path, old_ref, new_ref)
    objects = []

    Dir.chdir repo_path

    IO.popen(['git', 'diff-tree', '--ignore-submodules=all', '-r', old_ref, new_ref]).readlines.each do |line|
      (src_mode, dst_mode, src_hash, dst_hash, action, object_name) = line.split(" ")
      objects.push({
                     :src_mode => src_mode,
                     :dst_mode => dst_mode,
                     :src_hash => src_hash,
                     :dst_hash => dst_hash,
                     :action => action,
                     :object_name => object_name,
                   })
    end

    return objects
  end


  #
  # check if commit only contains deletes
  #
  def only_deletes(changed_objects)
    changed_objects.each do |obj|
      # Merge
      if obj[:action] == "M" or obj[:action] == "A"
        return false
      end
    end

    return true
  end


  #
  # get size of changed objects in mb
  #
  def changed_objects_size(changed_objects, repo_path)
    total = 0

    changed_objects.each do |obj|
      # Merge
      if obj[:action] == "M"
        total += git_object_size(repo_path, obj[:dst_hash]) - git_object_size(repo_path, obj[:src_hash])

      # Add
      elsif obj[:action] == "A"
        total += git_object_size(repo_path, obj[:dst_hash])

      # Delete
      elsif obj[:action] == "D"
        total -= git_object_size(repo_path, obj[:src_hash])
      end
    end

    return total
  end


  #
  # return size of git object in mb
  #
  def git_object_size(repo_path, my_hash)
    Dir.chdir repo_path

    f = IO.popen(['git', 'cat-file', '-s', my_hash])
    size = (f.read.to_i/1024/1024).to_i
    f.close

    return size
  end


  #
  # run garbadge collection on repo
  # return size in mb
  #
  def repo_size(repo_path)
    require 'find'
    size = 0

    if !File.directory?(repo_path)
      raise TypeError, repo_path + " is not a valid repository"
    end

    Dir.chdir repo_path
    system("git gc")

    Find.find(repo_path) { |f| size += File.size(f) if File.file?(f) }

    return (size/1024/1024).to_i
  end


  #
  # returns true if string is not valid ref in hex
  #
  def is_not_ref(mystr)
    return mystr[/\H/]
  end

  #
  # return true if ref is NULL ref (new branch)
  #
  def is_new_branch(mystr)
    return mystr == "0000000000000000000000000000000000000000"
  end

end
