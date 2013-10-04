#=========================================================================
# ast_tranformer.py
#=========================================================================
# Create a simplified representation of the Python AST for help with
# source to source translation.

import ast, _ast
import re

#-------------------------------------------------------------------------
# SimplifiedAST
#-------------------------------------------------------------------------
class SimplifiedAST( ast.NodeTransformer ):

  def __init__( self ):
    self.self_name   = None
    self.self_prefix = None

  def visit_Module( self, node ):
    # visit children
    self.generic_visit( node )
    # copy the function body, delete module references
    return ast.copy_location( node.body[0], node )

  def visit_FunctionDef( self, node ):
    # store self_name
    self.self_name   = node.args.args[0].id
    self.self_prefix = node.args.args[0].id + '.'
    # visit children
    self.generic_visit( node )
    new_node = ast.FunctionDef( name=node.name, args=node.args,
                                body=node.body, decorator_list=[] )
    # create a new function that deletes the decorators
    return new_node

  def visit_Attribute( self, node ):
    reverse_branch = ReorderAST().reverse( node )
    return ast.copy_location( reverse_branch, node )

  def visit_Subscript( self, node ):
    reverse_branch = ReorderAST().reverse( node )
    return ast.copy_location( reverse_branch, node )

  def visit_Name( self, node ):
    new_node = Local( id=node.id )
    return ast.copy_location( new_node, node )


#-------------------------------------------------------------------------
# ReorderAST
#-------------------------------------------------------------------------
# Reorders an AST branch beginning with the indicated node.  Intended
# for inverting the order of Name/Attribute chains so that the Name
# node comes first, followed by chains of Attribute/Subscript nodes.
#
# This visitor will also insert Self nodes to represent references to the
# self variable, and remove Index nodes which seem to serve no useful
# purpose.

class ReorderAST( ast.NodeVisitor ):

  def __init__( self ):
    self.stack = []

  def reverse( self, tree ):
    # Visit the tree
    self.visit( tree )

    # The top of the stack is the new root of the tree
    current = new_root = self.stack.pop()

    # Pop each node off the stack, update pointers
    while self.stack:
      next_         = self.stack.pop()
      current.value = next_
      current       = next_

    # Update the last pointer to None, return the new_root
    current.value = None
    return new_root

  def visit_Name( self, node ):
    self.stack.append( Self( attr=node.id ) )

  def visit_Attribute( self, node ):
    self.stack.append( node )
    self.visit( node.value )

  def visit_Subscript( self, node ):
    node.slice = ReorderAST().reverse( node.slice )
    self.stack.append( node )
    self.visit( node.value )

  def visit_Index( self, node ):
    # Index nodes are dumb.  Remove them by not adding them to the stack.
    self.visit( node.value )

  def visit_Slice( self, node ):
    assert node.step == None
    self.stack.append( node )
    node.lower = ReorderAST().reverse( node.lower )
    node.upper = ReorderAST().reverse( node.upper )

  def visit_Num( self, node ):
    self.stack.append( node )

#------------------------------------------------------------------------
# Self
#------------------------------------------------------------------------
# New AST Node for references to self. Based on Attribute node.
class Self( _ast.Attribute ):
  value = None

#------------------------------------------------------------------------
# Local
#------------------------------------------------------------------------
# New AST Node for local vars. Based on Name node.
class Local( _ast.Name ):
  pass
