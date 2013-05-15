#!/usr/bin/python

import sys
import subprocess
import os
import json
import copy

class Generator(object):
    """
    JSB Bytecode Generator Class
    """

    def __init__(self, options):
        """
        Arguments:
        - `options`:
        """
        self._current_src_dir = None
        self._src_dir_arr = options.src_dir_arr
        self._dst_dir = options.dst_dir
        self._use_closure_compiler = options.use_closure_compiler
        self._config = None
        if options.compiler_config != None:
            f = open(options.compiler_config)
            self._config = json.load(f)
            f.close()

        self._success = []
        self._failure = []
        self._js_files = {}
        self._compressed_js_path = os.path.join(self._dst_dir, options.compressed_filename)
        self._compressed_jsc_path = os.path.join(self._dst_dir, options.compressed_filename+"c")

    def get_relative_path(self, jsfile):
        try:
            # print "current src dir: "+self._current_src_dir
            pos = jsfile.index(self._current_src_dir)
            if pos != 0:
                raise Exception("cannot find src directory in file path.")
            # print "origin js path: "+ jsfile
            # print "relative path: "+jsfile[len(self._current_src_dir)+1:]
            return jsfile[len(self._current_src_dir)+1:]
        except ValueError:
            raise Exception("cannot find src directory in file path.")

    def get_output_file_path(self, jsfile):
        """
        Gets output file path by source js file
        """
        # create folder for generated file
        jsc_filepath = ""
        relative_path = self.get_relative_path(jsfile)+"c"
        jsc_filepath = os.path.join(self._dst_dir, relative_path)

        dst_rootpath = os.path.split(jsc_filepath)[0]
        try:
            # print "creating dir (%s)" % (dst_rootpath)
            os.makedirs(dst_rootpath)
        except OSError:
            if os.path.exists(dst_rootpath) == False:
                # There was an error on creation, so make sure we know about it
                raise Exception("Error: cannot create folder in "+dst_rootpath)

        # print "return jsc path: "+jsc_filepath
        return jsc_filepath

    def compile_js(self, jsfile, output_file):
        """
        Compiles js file
        """
        print "compiling js (%s) to bytecode..." % (jsfile)

        ret = subprocess.call("./jsbcc "+jsfile+" "+output_file, shell=True)
        if ret == 0:
            self._success.append(jsfile)
        else:
            self._failure.append(jsfile)
        print "----------------------------------------"

    def compress_js(self):
        """
        Compress all js files into one big file.
        """
        jsfiles = ""
        for src_dir in self._src_dir_arr:
            # print "\n----------src:"+src_dir
            jsfiles = jsfiles + " --js ".join(self._js_files[src_dir]) + " "

        compiler_jar_path = "compiler.jar"
        command = "java -jar %s --js %s --js_output_file %s" % (compiler_jar_path, jsfiles, self._compressed_js_path)
        print "\ncommand:"+command+"\n"

        ret = subprocess.call(command, shell=True)
        if ret == 0:
            print "js files were compressed successfully..."
        else:
            print "js files were compressed unsuccessfully..."

    def deep_iterate_dir(self, rootDir):
        for lists in os.listdir(rootDir):
            path = os.path.join(rootDir, lists)
            if os.path.isdir(path):
                self.deep_iterate_dir(path)
            elif os.path.isfile(path):
                if os.path.splitext(path)[1] == ".js":
                    self._js_files[self._current_src_dir].append(path)


    def js_filename_pre_order_compare(self, a, b):
        """
        """
        pre_order = self._config["pre_order"]

        if a in pre_order and not b in pre_order:
            return -1
        elif not a in pre_order and b in pre_order:
            return 1
        elif a in pre_order and b in pre_order:
            if pre_order.index(a) > pre_order.index(b):
                return 1
            elif pre_order.index(a) < pre_order.index(b):
                return -1
            else:
                return 0
        else:
            return 0


    def js_filename_post_order_compare(self, a, b):
        """
        """
        post_order = self._config["post_order"]

        if a in post_order and not b in post_order:
            return 1
        elif not a in post_order and b in post_order:
            return -1
        elif a in post_order and b in post_order:
            if post_order.index(a) > post_order.index(b):
                return 1
            elif post_order.index(a) < post_order.index(b):
                return -1
            else:
                return 0
        else:
            return 0

    def reorder_js_files(self):
        if self._config == None:
            return

        # print "before:"+str(self._js_files)

        for src_dir in self._js_files:
            # Remove file in exclude list
            need_remove_arr = []
            for jsfile in self._js_files[src_dir]:
                for exclude_file in self._config["skip"]:
                    if jsfile.find(exclude_file) != -1:
                        # print "remove:" + jsfile
                        need_remove_arr.append(jsfile)

            for need_remove in need_remove_arr:
                self._js_files[src_dir].remove(need_remove)

            if (self._config != None):
                self._js_files[src_dir].sort(cmp=self.js_filename_pre_order_compare)
                self._js_files[src_dir].sort(cmp=self.js_filename_post_order_compare)

        # print '-------------------'
        # print "after:" + str(self._js_files)

    def handle_all_js_files(self):
        """
        Arguments:
        - `self`:
        """
        if self._use_closure_compiler == True:
            self.compress_js()
            self.compile_js(self._compressed_js_path, self._compressed_jsc_path)
            # remove tmp compressed file
            os.remove(self._compressed_js_path)
        else:
            for src_dir in self._src_dir_arr:
                for jsfile in self._js_files[src_dir]:
                    self._current_src_dir = src_dir
                    self.compile_js(jsfile, self.get_output_file_path(jsfile))

    def run(self):
        """
        """
        # create output directory
        try:
            os.makedirs(self._dst_dir)
        except OSError:
            if os.path.exists(self._dst_dir) == False:
                raise Exception("Error: cannot create folder in "+self._dst_dir)

        # deep iterate the src directory
        for src_dir in self._src_dir_arr:
            self._current_src_dir = src_dir
            self._js_files[self._current_src_dir] = []
            self.deep_iterate_dir(src_dir)

        self.reorder_js_files()
        self.handle_all_js_files()
        print "\nCompilation finished, (%d) files succeed, (%d) files fail." % (len(self._success), len(self._failure))
        if len(self._failure) > 0:
            print "Failure files are:"
            print self._failure
        print "------------------------------"

def main():
    """
    """
    from optparse import OptionParser

    parser = OptionParser("usage: %prog -s src_dir [-d dst_dir -c use_closure_compiler]")
    parser.add_option("-s", "--src",
                      action="append", type="string", dest="src_dir_arr",
                      help="source directory of js files needed to be compiled")

    parser.add_option("-d", "--dst",
                      action="store", type="string", dest="dst_dir",
                      help="destination directory of js bytecode files to be stored")

    parser.add_option("-c", "--use_closure_compiler",
                      action="store_true", dest="use_closure_compiler", default=False,
                      help="Whether to use closure compiler to compress all js files into just a big file")

    parser.add_option("-o", "--output_compressed_filename",
                      action="store", dest="compressed_filename", default="game.js",
                      help="Only available when '-c' option was True")

    parser.add_option("-j", "--compiler_config",
                      action="store", dest="compiler_config",
                      help="The configuration for closure compiler")

    (options, args) = parser.parse_args()

    # print options

    if options.src_dir_arr == None:
        raise Exception("Please set source folder by \"-s\" or \"-src\", run ./jscompile.py -h for the usage ")
    elif options.dst_dir == None:
        raise Exception("Please set destination folder by \"-d\" or \"-dst\", run ./jscompile.py -h for the usage ")
    else:
        for src_dir in options.src_dir_arr:
            if os.path.exists(src_dir) == False:
                raise Exception("Error: dir (%s) doesn't exist..." % (src_dir))


    generator = Generator(options)
    generator.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print e
        sys.exit(1)
