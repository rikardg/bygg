# Why Bygg

## Why should you consider using it?

Short version: if you have a set of diverse tools that you need to connect
together, you might end up writing glue code in Python to do so. If you do,
then Bygg might be a good choice for describing and executing the build graph.

## Why should you not use it?

Many reasons!

If you only need a task runner, there are many others. Just pick one whose
syntax you like and that integrates well with your workflow. However, Bygg is
also a task runner, and if the syntax is ok with you, then it gives the
possibility to start using the rest of the system over time.

If your build needs are covered by a general tool like Make or one of the many
tools like it, you are probably fine with them. There are many tools that are
specialised for certain programming languages and that aim to give help writing
rules for them, like Meson/Cargo/Gobuild.

## Why another one?

One of my use cases was to execute a set of build pipelines in a monorepo with
parts doing Jinja templating, TypeScript compilation, some Node tools, and then
compilation for Android and iOS. In addition quite a lot of Python code to
cover the gaps.

## Background

It started from a moment of insight that the Make system I maintained had
become increasingly complicated to work on.

This was mainly due to a few factors, I think:

- Make has no good way of compartmentalising code. Yes, we can split out parts
  into separate files, but the namespace is still shared.
- Using functions is possible, but not really convenient. Variables need to be
  double-escaped if they're supposed to be evaluated first in the generated
  rule, for example.

As for other people not being able to work on it, I think it is mainly due to
that the Makefile syntax is a bit archaic, and working with it and Make's
peculiarities requires a certain state of mind.
