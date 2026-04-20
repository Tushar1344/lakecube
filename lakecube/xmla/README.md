# Legacy XMLA / MDX Bridge

A thin translator service so existing Smart View (classic), Excel OLAP pivots,
Power BI Premium, and third-party MDX clients connect to Lakecube unchanged
during migration. Built on [olap4j](http://www.olap4j.org/) / [Mondrian](https://mondrian.pentaho.com/) MDX parsing.

Not a core plane — a migration ramp. Covers the 80/20 of Essbase MDX; flags
unsupported constructs with pointers to native Lakecube equivalents.

**Status**: lands in P4.
