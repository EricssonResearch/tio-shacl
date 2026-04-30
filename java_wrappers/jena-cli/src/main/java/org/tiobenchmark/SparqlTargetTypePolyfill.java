package org.tiobenchmark;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.jena.graph.Graph;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.vocabulary.RDF;

/**
 * Generic SHACL-AF {@code sh:SPARQLTargetType} polyfill.
 *
 * <p>Apache Jena's SHACL implementation does not evaluate parameterised
 * {@code sh:SPARQLTargetType} instances. This class pre-processes the shapes
 * graph before handing it to Jena, rewriting every target-type instance as an
 * inline {@code sh:SPARQLTarget} with the parameter values substituted into the
 * target type's {@code sh:select} template.</p>
 *
 * <p>The algorithm is a faithful application of the SHACL Advanced Features
 * specification
 * (<a href="https://www.w3.org/TR/shacl-af/#SPARQLTargetType">W3C SHACL-AF §4.2</a>)
 * and is not TIO-specific.</p>
 *
 * <h2>Algorithm</h2>
 * <ol>
 *   <li>Enumerate every class {@code T} declared {@code a sh:SPARQLTargetType}.</li>
 *   <li>Read {@code T}'s {@code sh:select} template and its
 *       {@code sh:parameter} list. Each parameter exposes
 *       {@code sh:path <propIRI>} and {@code sh:name "paramName"}.</li>
 *   <li>Find every target node {@code t} such that {@code ?shape sh:target ?t}
 *       and {@code ?t a T}.</li>
 *   <li>For each such {@code t}, read the bound parameter values via the
 *       {@code sh:path} properties and substitute them into the template. The
 *       placeholder is the parameter name with a {@code $} prefix.</li>
 *   <li>Replace the triples describing {@code t} with
 *       {@code t a sh:SPARQLTarget ; sh:select "SELECT ..."}.</li>
 * </ol>
 */
public final class SparqlTargetTypePolyfill {

    private static final String SH = "http://www.w3.org/ns/shacl#";
    private static final Node SPARQL_TARGET_TYPE = NodeFactory.createURI(SH + "SPARQLTargetType");
    private static final Node SPARQL_TARGET = NodeFactory.createURI(SH + "SPARQLTarget");
    private static final Node SH_TARGET = NodeFactory.createURI(SH + "target");
    private static final Node SH_SELECT = NodeFactory.createURI(SH + "select");
    private static final Node SH_PARAMETER = NodeFactory.createURI(SH + "parameter");
    private static final Node SH_PATH = NodeFactory.createURI(SH + "path");
    private static final Node SH_NAME = NodeFactory.createURI(SH + "name");

    private SparqlTargetTypePolyfill() {}

    /**
     * Rewrite every {@code sh:SPARQLTargetType} instance in {@code shapes}
     * as an inline {@code sh:SPARQLTarget}. The graph is mutated in place.
     *
     * @return the number of target-type instances that were converted.
     */
    public static int apply(Graph shapes) {
        Map<Node, TargetType> targetTypes = collectTargetTypes(shapes);
        if (targetTypes.isEmpty()) {
            return 0;
        }
        return rewriteTargets(shapes, targetTypes);
    }

    // -------------------------------------------------------------------
    // Step 1-2: collect target-type definitions
    // -------------------------------------------------------------------

    private static Map<Node, TargetType> collectTargetTypes(Graph g) {
        Map<Node, TargetType> out = new HashMap<>();
        Iterator<Triple> types = g.find(Node.ANY, RDF.type.asNode(), SPARQL_TARGET_TYPE);
        while (types.hasNext()) {
            Node typeNode = types.next().getSubject();
            String template = firstLiteralLexical(g, typeNode, SH_SELECT);
            if (template == null) {
                continue;
            }
            List<Parameter> params = readParameters(g, typeNode);
            out.put(typeNode, new TargetType(typeNode, template, params));
        }
        return out;
    }

    private static List<Parameter> readParameters(Graph g, Node typeNode) {
        List<Parameter> out = new ArrayList<>();
        Iterator<Triple> it = g.find(typeNode, SH_PARAMETER, Node.ANY);
        while (it.hasNext()) {
            Node paramNode = it.next().getObject();
            Node path = firstObject(g, paramNode, SH_PATH);
            String name = firstLiteralLexical(g, paramNode, SH_NAME);
            if (path != null && name != null && path.isURI()) {
                out.add(new Parameter(path, name));
            }
        }
        return out;
    }

    // -------------------------------------------------------------------
    // Step 3-5: rewrite every matching target instance
    // -------------------------------------------------------------------

    private static int rewriteTargets(Graph g, Map<Node, TargetType> targetTypes) {
        // Collect rewrites first to avoid mutating while iterating.
        List<Rewrite> rewrites = new ArrayList<>();

        for (TargetType type : targetTypes.values()) {
            Iterator<Triple> instances = g.find(Node.ANY, RDF.type.asNode(), type.node);
            while (instances.hasNext()) {
                Node targetNode = instances.next().getSubject();
                // Only rewrite target nodes that actually occupy a sh:target slot.
                if (!isUsedAsTarget(g, targetNode)) {
                    continue;
                }
                Map<String, Node> bindings = readBindings(g, targetNode, type.parameters);
                if (bindings.size() != type.parameters.size()) {
                    // Under-specified — leave it alone; Jena's native error is
                    // more informative than a silently wrong rewrite.
                    continue;
                }
                String sparql = substitute(type.template, bindings);
                rewrites.add(new Rewrite(targetNode, type, sparql));
            }
        }

        for (Rewrite r : rewrites) {
            applyRewrite(g, r);
        }
        return rewrites.size();
    }

    private static boolean isUsedAsTarget(Graph g, Node targetNode) {
        return g.contains(Node.ANY, SH_TARGET, targetNode);
    }

    private static Map<String, Node> readBindings(Graph g, Node targetNode, List<Parameter> params) {
        Map<String, Node> out = new LinkedHashMap<>();
        for (Parameter p : params) {
            Node value = firstObject(g, targetNode, p.path);
            if (value != null) {
                out.put(p.name, value);
            }
        }
        return out;
    }

    private static String substitute(String template, Map<String, Node> bindings) {
        String result = template;
        for (Map.Entry<String, Node> e : bindings.entrySet()) {
            String placeholder = "$" + e.getKey();
            result = result.replace(placeholder, nodeToSparqlLiteral(e.getValue()));
        }
        return result;
    }

    private static String nodeToSparqlLiteral(Node n) {
        if (n.isURI()) {
            return "<" + n.getURI() + ">";
        }
        if (n.isLiteral()) {
            String lex = n.getLiteralLexicalForm();
            String dt = n.getLiteralDatatypeURI();
            String lang = n.getLiteralLanguage();
            String escaped = escapeTurtleString(lex);
            if (lang != null && !lang.isEmpty()) {
                return "\"" + escaped + "\"@" + lang;
            }
            if (dt != null && !dt.isEmpty()
                && !dt.equals("http://www.w3.org/2001/XMLSchema#string")) {
                return "\"" + escaped + "\"^^<" + dt + ">";
            }
            return "\"" + escaped + "\"";
        }
        // Blank nodes cannot appear in a SELECT projection literal — fall back
        // to an IRI form that Jena will still parse; the target will match
        // nothing, mimicking pyshacl's behaviour on an unbound blank node.
        return "<" + n.toString() + ">";
    }

    private static String escapeTurtleString(String s) {
        StringBuilder b = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '\\': b.append("\\\\"); break;
                case '"': b.append("\\\""); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default: b.append(c);
            }
        }
        return b.toString();
    }

    private static void applyRewrite(Graph g, Rewrite r) {
        // Remove every triple with targetNode as subject; this wipes the
        // rdf:type and every parameter binding.
        List<Triple> toRemove = new ArrayList<>();
        Iterator<Triple> it = g.find(r.targetNode, Node.ANY, Node.ANY);
        while (it.hasNext()) {
            toRemove.add(it.next());
        }
        for (Triple t : toRemove) {
            g.delete(t);
        }

        // Add the rewritten triples.
        g.add(Triple.create(r.targetNode, RDF.type.asNode(), SPARQL_TARGET));
        g.add(Triple.create(r.targetNode, SH_SELECT,
            NodeFactory.createLiteralString(r.sparql)));
    }

    // -------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------

    private static Node firstObject(Graph g, Node s, Node p) {
        Iterator<Triple> it = g.find(s, p, Node.ANY);
        return it.hasNext() ? it.next().getObject() : null;
    }

    private static String firstLiteralLexical(Graph g, Node s, Node p) {
        Node o = firstObject(g, s, p);
        return (o != null && o.isLiteral()) ? o.getLiteralLexicalForm() : null;
    }

    // -------------------------------------------------------------------
    // Records
    // -------------------------------------------------------------------

    private record Parameter(Node path, String name) {}

    private record TargetType(Node node, String template, List<Parameter> parameters) {}

    private record Rewrite(Node targetNode, TargetType type, String sparql) {}
}
