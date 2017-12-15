# [bracket]

The syntax of Clojure [mostly], the engine of Python, and  the language is designed so you [mostly] never have to hit the "shift" key.  

Heavily "inspired by" [stolen from] Peter Norvig's [articles](http://norvig.com/lispy2.html) and Dave Beazely's [course](http://www.dabeaz.com/chicago/sicp.html) on SICP.

#### Requirements
* Python 3.6+
* Libraries:
	* naga
	
#### Quickstart

    git clone https://github.com/HiImJayHireMe/bracket
    cd bracket
    python3.6 -O bracket.py
    
 If I haven't broken anything, you should see a REPL pop up.  
 
     $->
 
 Go ahead and try some stuff!
 
	$->  5
	;;=> 5
	$->  [add 5 1]
	;;=> 6
	$->  [- 5 1]
	;;=> 4

Maybe try some fancier stuff!

	$->  [let [a [add 1 2]
               b [add a 1]
               c [add a b]]
          [add a b c]]
	;;=> 14

**[bracket]** also supports assignments.

	$->  [def name 'taco']
	$->  [defn hello [name] [pformat 'hello {}' name]]
	$->  [hello name]
	hello taco

You can even get a little fancy with recursion.  Which is good, because I haven't included looping constructs yet.

	$->  [defn fib [n]
  	           [if [< n 2]
	               n
	               [add [fib [- n 2]]
	                    [fib [- n 1]]]]]
	$->  [fib 10]
	;;=> 55
	$->  [fib 20]
	;;=> 6765

Go crazy with tail recursion!

    $->  [defn sum [acc xs]
           [if [= 0 [count xs]]
               acc
               [sum [add acc [first xs]] [rest xs]]]]
    $->  [sum 0 [range 10000]]
    ;;=> 49995000
    
Take advantage of arrity-based dispatch!

    $->  [defn xsum 
           [[n]
            [xsum 0 [range n]]]
           [[acc xs]
            [if [= 0 [count xs]]
                acc
                [xsum [add acc [first xs]] [rest xs]]]]]
    $->  [xsum 10]
    ;;=> 45
    $->  [xsum 10000]
    ;;=> 49995000

Arrity can be variadic!

    $->  [defn foo 
           [[a b] [add a b]]
           [[a . b] [foo a [reduce add b]]]]
    $->  [foo 1 2 3]
    ;;=> 6


You can name your destructured items

    $->  [defn foo [[a b c -as x]] [list a b c x]]
    $->  [foo /[1 2 3 4]]
    ;;=> [1, 2, 3, [1, 2, 3, 4]]


#### Roadmap

* [x] Implement tail recursion
* [x] List literals
* [x] multi-arrity dispatch
* [x] Implement destructuring _a la_ Clojure
* [x] Variadic arguments
* [x] Improved destructuring
* [ ] Namespacing/modules
* [ ] Native Python interop
* [ ] User defined macros
* [ ] Map literals
* [ ] iterator constructs ("`for`" special form)
* [ ] better apply method
* [ ] Export bracket to Python
* [ ] Concurrency support
* [ ] Useful stack traces
* [ ] Editor support
* [ ] Export bracket to Clojure (maybe?)
* [ ] ...?
* [ ] profit!